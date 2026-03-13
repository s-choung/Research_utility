"""하이브레인넷 채용공고 모니터링"""

from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from common import HEADERS, SCRIPT_DIR, load_json, save_json, log

BASE_URL = "https://www.hibrain.net"
LIST_URL = BASE_URL + "/recruitment/recruits"
DATA_FILE = SCRIPT_DIR / "seen_hibrain.json"

LIST_TYPES = {
    "RECOMM": "추천",
    "D3NEW": "신규",
}

# --- 대학 필터 (THE/QS/ARWU 2025-2026 한국 Top 20) ---
TARGET_UNIVERSITIES = [
    "서울대", "서울대학교", "Seoul National",
    "KAIST", "카이스트", "한국과학기술원",
    "연세대", "연세대학교", "Yonsei",
    "성균관대", "성균관대학교", "Sungkyunkwan",
    "POSTECH", "포항공대", "포항공과대학교",
    "고려대", "고려대학교", "Korea University",
    "UNIST", "울산과학기술원",
    "한양대", "한양대학교", "Hanyang",
    "경희대", "경희대학교", "Kyung Hee",
    "세종대", "세종대학교", "Sejong University",
    "DGIST", "대구경북과학기술원",
    "아주대", "아주대학교", "Ajou",
    "중앙대", "중앙대학교", "Chung-Ang",
    "GIST", "광주과학기술원",
    "이화여대", "이화여자대학교", "Ewha",
    "건국대", "건국대학교", "Konkuk",
    "경북대", "경북대학교", "Kyungpook",
    "부산대", "부산대학교", "Pusan National",
    "울산대", "울산대학교", "University of Ulsan",
    "가톨릭대", "가톨릭대학교", "Catholic Univ",
    "서강대", "서강대학교", "Sogang",
    "인하대", "인하대학교", "Inha",
    "전남대", "전남대학교", "Chonnam",
    "영남대", "영남대학교", "Yeungnam",
]

POSITION_KEYWORDS = [
    "전임교원", "전임교수", "전임직교원", "전임직 교원",
    "교수 초빙", "교수 특별초빙", "교수 공개초빙",
    "교원 초빙", "교원 공개초빙",
]

EXCLUDE_POSITION = [
    "Post-Doc", "PostDoc", "post-doc", "postdoc",
    "박사후", "연구교수",
    "박사급 연구원", "박사급 인재", "연구원 모집", "연구원 채용",
    "전임연구원", "비전임",
]

# 분교/캠퍼스 키워드: "서울"이 함께 있으면 통과
EXCLUDE_CAMPUS = [
    "세종캠퍼스", "세종캠", "ERICA", "에리카",
    "글로벌캠퍼스", "국제캠퍼스",
    "천안캠퍼스", "삼성캠퍼스",
]

EXCLUDE_FIELDS = [
    "의과대학", "의대", "의학과", "의학전문",
    "간호대학", "간호학과", "간호대",
    "약학대학", "약학과", "약대",
    "치과대학", "치의학", "치대",
    "수의과대학", "수의학", "수의대",
    "법학", "법과대학", "법대", "로스쿨",
    "음악대학", "음악학과", "음대",
    "미술대학", "미술학과", "미대", "디자인학과",
    "체육", "스포츠",
    "신학", "종교",
    "사범대학", "교육대학", "사범대",
    "경찰", "군사",
]


def _matches_university(title: str) -> bool:
    return any(uni in title for uni in TARGET_UNIVERSITIES)


def _is_faculty(title: str) -> bool:
    return any(kw in title for kw in POSITION_KEYWORDS)


def _is_excluded(title: str) -> bool:
    title_lower = title.lower()
    if any(kw.lower() in title_lower for kw in EXCLUDE_POSITION):
        return True
    # 분교 키워드가 있어도 "서울"이 함께 있으면 통과
    if any(kw.lower() in title_lower for kw in EXCLUDE_CAMPUS):
        if "서울" not in title:
            return True
    if any(kw in title for kw in EXCLUDE_FIELDS):
        return True
    return False


def _fetch_page(list_type: str, page: int = 1) -> str:
    params = {
        "listType": list_type,
        "sortType": "SORTDTM",
        "displayType": "TIT",
        "limit": "25",
        "siteid": "1",
        "page": str(page),
    }
    resp = requests.get(LIST_URL, params=params, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.text


def _parse_posts(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    article_list = soup.find("ul", id="articleList")
    if not article_list:
        return []

    posts = []
    for li in article_list.find_all("li", recursive=False):
        if "tableheader" in li.get("class", []):
            continue
        title_span = li.find("span", class_="td_title")
        if not title_span:
            continue
        link_tag = title_span.find("a")
        if not link_tag:
            continue

        title = link_tag.get("title", link_tag.get_text(strip=True))
        href = link_tag.get("href", "")
        post_id = ""
        if "/recruits/" in href:
            post_id = href.split("/recruits/")[1].split("?")[0]

        receipt_span = li.find("span", class_="td_receipt")
        receipt = receipt_span.get_text(strip=True) if receipt_span else ""
        rdtm_span = li.find("span", class_="td_rdtm")
        rdtm = rdtm_span.get_text(strip=True) if rdtm_span else ""

        posts.append({
            "id": post_id,
            "title": title,
            "url": urljoin(BASE_URL, href),
            "receipt": receipt,
            "date": rdtm,
        })
    return posts


def check_new() -> list[dict]:
    """새 채용공고 확인 (필터 적용)"""
    seen = load_json(DATA_FILE)
    all_new = []

    for lt, label in LIST_TYPES.items():
        log(f"[하이브레인/{label}] 확인 중...")
        for page in range(1, 4):
            html = _fetch_page(lt, page)
            posts = _parse_posts(html)
            if not posts:
                break
            for post in posts:
                if post["id"] and post["id"] not in seen:
                    matched = (
                        _matches_university(post["title"])
                        and _is_faculty(post["title"])
                        and not _is_excluded(post["title"])
                    )
                    if matched and post["id"] not in [p["id"] for p in all_new]:
                        all_new.append(post)
                    seen[post["id"]] = {
                        "title": post["title"],
                        "date": post["date"],
                        "first_seen": datetime.now().isoformat(),
                        "matched": matched,
                    }

    save_json(DATA_FILE, seen)
    log(f"[하이브레인] 새 공고 {len(all_new)}건")
    return all_new


def init():
    """기존 공고를 모두 본 것으로 기록"""
    seen = load_json(DATA_FILE)
    for lt, label in LIST_TYPES.items():
        for page in range(1, 4):
            html = _fetch_page(lt, page)
            posts = _parse_posts(html)
            if not posts:
                break
            for post in posts:
                if post["id"] and post["id"] not in seen:
                    seen[post["id"]] = {
                        "title": post["title"],
                        "date": post["date"],
                        "first_seen": datetime.now().isoformat(),
                    }
        save_json(DATA_FILE, seen)
        log(f"[하이브레인/{label}] {len(seen)}개 기록 완료")
