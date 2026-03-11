"""공통 유틸리티 (알림, 로그, HTML 요약)"""

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
LOG_FILE = SCRIPT_DIR / "monitor.log"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}

_notify_counter = 0


def log(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_json(path: Path) -> dict:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_json(path: Path, data: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def mac_notify(title: str, message: str, url: str = ""):
    global _notify_counter
    _notify_counter += 1
    try:
        cmd = [
            "terminal-notifier",
            "-title", title,
            "-message", message,
            "-sound", "default",
            "-group", f"monitor-{_notify_counter}",
        ]
        if url:
            cmd += ["-open", url]
        subprocess.run(cmd, check=True, capture_output=True)
    except FileNotFoundError:
        script = f'display notification "{message}" with title "{title}" sound name "default"'
        subprocess.run(["osascript", "-e", script], check=False)


def send_notifications(posts: list[dict], source: str):
    """개별 알림 발송"""
    for post in posts:
        mac_notify(
            title=f"{source} 새 공고 ({len(posts)}건 중)",
            message=f"{post['title']}\n{post.get('receipt', '')}",
            url=post["url"],
        )
        time.sleep(0.5)


def open_summary(sections: list[tuple[str, str, list[dict]]]):
    """여러 섹션의 공고를 HTML 요약 페이지로 열기.
    sections: [(섹션 제목, CSS 색상, posts), ...]
    """
    html_path = SCRIPT_DIR / "summary.html"
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    total = sum(len(posts) for _, _, posts in sections)

    body_parts = []
    for title, color, posts in sections:
        if not posts:
            block = f'<h2>{title} (0건)</h2><div class="empty">새 공고가 없습니다.</div>'
        else:
            rows = ""
            for i, p in enumerate(posts, 1):
                rows += (
                    f'<tr onclick="window.open(\'{p["url"]}\', \'_blank\')" style="cursor:pointer">'
                    f'<td>{i}</td>'
                    f'<td><a href="{p["url"]}" target="_blank">{p["title"]}</a></td>'
                    f'<td>{p.get("receipt", "")}</td></tr>'
                )
            block = (
                f'<h2>{title} ({len(posts)}건)</h2>'
                f'<table><tr><th style="background:{color}">#</th>'
                f'<th style="background:{color}">제목</th>'
                f'<th style="background:{color}">접수</th></tr>{rows}</table>'
            )
        body_parts.append(block)

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>공고 알림 - {today}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 40px auto; max-width: 720px; background: #f5f5f7; }}
  h1 {{ font-size: 22px; color: #1d1d1f; }}
  h2 {{ font-size: 17px; color: #1d1d1f; margin-top: 32px; }}
  .info {{ color: #86868b; margin-bottom: 20px; }}
  table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 24px; }}
  th {{ color: white; padding: 12px 16px; text-align: left; font-weight: 500; }}
  td {{ padding: 12px 16px; border-bottom: 1px solid #f0f0f0; }}
  tr:hover td {{ background: #f0f7ff; }}
  a {{ color: #0071e3; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  .empty {{ text-align: center; padding: 40px; color: #86868b; }}
  .footer {{ margin-top: 40px; padding: 16px 0; color: rgba(0,0,0,0.3); font-size: 12px; text-align: center; }}
</style>
</head>
<body>
<h1>새 공고 알림</h1>
<p class="info">{today} 기준 | 총 {total}건</p>
{"".join(body_parts)}
<div class="footer">파싱 시각: {today}</div>
</body>
</html>"""

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    subprocess.run(["open", str(html_path)], check=False)
