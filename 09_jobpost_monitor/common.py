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


def open_summary(sections: list[tuple], auto_open: bool = True):
    """여러 섹션의 공고를 HTML 요약 페이지로 열기.
    sections: [(섹션 제목, CSS 색상, posts, new_count), ...]
    """
    html_path = SCRIPT_DIR / "summary.html"
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    total = sum(len(posts) for _, _, posts, _ in sections)
    total_new = sum(nc for _, _, _, nc in sections)

    body_parts = []
    for title, color, posts, new_count in sections:
        if not posts:
            block = f'<h2>{title} (0건)</h2><div class="empty">새 공고가 없습니다.</div>'
        else:
            new_badge = f' <span class="new-badge">+{new_count} NEW</span>' if new_count else ''
            rows = ""
            for i, p in enumerate(posts, 1):
                is_new = i <= new_count
                new_cls = ' class="new-row"' if is_new else ''
                new_tag = '<span class="new-tag">NEW</span> ' if is_new else ''
                pid = p.get("id", "")
                rows += (
                    f'<tr id="row-{pid}"{new_cls}>'
                    f'<td>{i}</td>'
                    f'<td>{new_tag}<a href="{p["url"]}" target="_blank">{p["title"]}</a></td>'
                    f'<td>{p.get("receipt", "")}</td>'
                    f'<td><button class="hide-btn" onclick="hidePost(event, \'{pid}\')">숨기기</button></td></tr>'
                )
            block = (
                f'<h2>{title} ({len(posts)}건){new_badge}</h2>'
                f'<table><tr><th style="background:{color}">#</th>'
                f'<th style="background:{color}">제목</th>'
                f'<th style="background:{color}">접수</th>'
                f'<th style="background:{color}"></th></tr>{rows}</table>'
            )
        body_parts.append(block)

    new_info = f" | 새 공고 {total_new}건" if total_new else ""

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
  .new-badge {{ background: #ff3b30; color: white; font-size: 12px; padding: 2px 8px; border-radius: 10px; margin-left: 8px; }}
  .new-tag {{ background: #ff3b30; color: white; font-size: 11px; padding: 1px 6px; border-radius: 4px; }}
  .new-row td {{ background: #fff8f0; }}
  table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 24px; }}
  th {{ color: white; padding: 12px 16px; text-align: left; font-weight: 500; }}
  td {{ padding: 12px 16px; border-bottom: 1px solid #f0f0f0; }}
  tr:hover td {{ background: #f0f7ff; }}
  a {{ color: #0071e3; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  .empty {{ text-align: center; padding: 40px; color: #86868b; }}
  .hide-btn {{ background: none; border: 1px solid #ccc; color: #86868b; font-size: 12px; padding: 4px 10px; border-radius: 6px; cursor: pointer; white-space: nowrap; }}
  .hide-btn:hover {{ background: #ff3b30; color: white; border-color: #ff3b30; }}
  .hidden-row td {{ opacity: 0.3; text-decoration: line-through; }}
  .footer {{ margin-top: 40px; padding: 16px 0; color: rgba(0,0,0,0.3); font-size: 12px; text-align: center; }}
</style>
</head>
<body>
<h1>공고 모니터링</h1>
<p class="info">{today} 기준 | 누적 {total}건{new_info}</p>
{"".join(body_parts)}
<div class="footer">파싱 시각: {today}</div>
<script>
function hidePost(e, id) {{
  e.stopPropagation();
  fetch('http://localhost:19823/hide?id=' + encodeURIComponent(id))
    .then(r => r.json())
    .then(() => {{
      const row = document.getElementById('row-' + id);
      if (row) {{
        row.classList.add('hidden-row');
        row.querySelector('.hide-btn').textContent = '숨김';
        row.querySelector('.hide-btn').disabled = true;
      }}
    }})
    .catch(() => alert('서버 연결 실패. Raycast에서 Run Jobpost Monitor로 실행해주세요.'));
}}
</script>
</body>
</html>"""

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    if auto_open:
        subprocess.run(["open", str(html_path)], check=False)
