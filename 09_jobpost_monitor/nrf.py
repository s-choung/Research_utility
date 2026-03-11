"""NRF(한국연구재단) 신규사업공모 모니터링"""

from datetime import datetime

import requests
from bs4 import BeautifulSoup

from common import HEADERS, SCRIPT_DIR, load_json, save_json, log

NRF_URL = "https://www.nrf.re.kr/biz/notice/list"
NRF_VIEW_URL = "https://www.nrf.re.kr/biz/notice/view"
NRF_MENU_NO = "362"  # 신규사업공모
DATA_FILE = SCRIPT_DIR / "seen_nrf.json"

# 제외 키워드 (무관 분야만)
EXCLUDE_KEYWORDS = [
    "인문", "사회", "문학", "역사", "철학", "어문", "국문",
    "토양", "농업", "농촌", "수산", "해양", "산림",
    "심사시스템", "JAMS",
]


def _fetch() -> str:
    params = {
        "menu_no": NRF_MENU_NO,
        "bizSearchRegDttmAllYn": "Y",
        "searchRegYearDttm": str(datetime.now().year),
    }
    resp = requests.get(NRF_URL, params=params, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.text


def _parse(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    blocks = soup.find_all("div", class_="public-notice-block")
    posts = []
    for b in blocks:
        # 상태 (접수중, 접수마감 등)
        state_div = b.find("div", class_="state-block")
        status = state_div.get_text(strip=True) if state_div else ""

        # 제목 + post_no
        link = b.find("a", class_="view_btn")
        if not link:
            continue
        title = link.get_text(strip=True)
        post_no = link.get("data-post_no", "")
        biz_no = link.get("data-biz_no", "0")

        url = f"{NRF_VIEW_URL}?ac=view&postNo={post_no}&menuNo={NRF_MENU_NO}&bizNo={biz_no}"

        posts.append({
            "id": f"nrf_{post_no}",
            "title": title,
            "url": url,
            "receipt": status,
        })
    return posts


def check_new() -> list[dict]:
    """새 신규사업공모 확인"""
    seen = load_json(DATA_FILE)
    log("[NRF] 신규사업공모 확인 중...")

    html = _fetch()
    posts = _parse(html)

    new_posts = []
    for post in posts:
        if post["id"] not in seen:
            excluded = any(kw in post["title"] for kw in EXCLUDE_KEYWORDS)
            if not excluded:
                new_posts.append(post)
            seen[post["id"]] = {
                "title": post["title"],
                "status": post["receipt"],
                "first_seen": datetime.now().isoformat(),
                "excluded": excluded,
            }

    save_json(DATA_FILE, seen)
    log(f"[NRF] 새 공고 {len(new_posts)}건")
    return new_posts


def init():
    """기존 공고를 모두 본 것으로 기록"""
    seen = load_json(DATA_FILE)
    html = _fetch()
    posts = _parse(html)
    for post in posts:
        if post["id"] not in seen:
            seen[post["id"]] = {
                "title": post["title"],
                "status": post["receipt"],
                "first_seen": datetime.now().isoformat(),
            }
    save_json(DATA_FILE, seen)
    log(f"[NRF] {len(seen)}개 기록 완료")
