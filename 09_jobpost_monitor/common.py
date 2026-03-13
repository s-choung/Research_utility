"""공통 유틸리티 (알림, 로그, HTML 요약)"""

import json
import re
import subprocess
import time
from datetime import datetime, date
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


def _calc_dday(receipt: str) -> str:
    """접수 마감일에서 D-day 계산. 예: '26.03.12~26.03.26' → 'D-13'"""
    # 마지막 날짜 패턴 찾기 (YY.MM.DD)
    matches = re.findall(r'(\d{2})\.(\d{2})\.(\d{2})', receipt)
    if not matches:
        return ""
    yy, mm, dd = matches[-1]  # 마지막 날짜 = 마감일
    try:
        deadline = date(2000 + int(yy), int(mm), int(dd))
        diff = (deadline - date.today()).days
        if diff < 0:
            return '<span class="dday expired">마감</span>'
        elif diff == 0:
            return '<span class="dday urgent">D-Day</span>'
        elif diff <= 3:
            return f'<span class="dday urgent">D-{diff}</span>'
        elif diff <= 7:
            return f'<span class="dday soon">D-{diff}</span>'
        else:
            return f'<span class="dday">D-{diff}</span>'
    except ValueError:
        return ""


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
                receipt = p.get("receipt", "")
                dday = _calc_dday(receipt)
                rows += (
                    f'<tr id="row-{pid}"{new_cls}>'
                    f'<td>{i}</td>'
                    f'<td>{new_tag}<a href="{p["url"]}" target="_blank">{p["title"]}</a></td>'
                    f'<td>{receipt}</td>'
                    f'<td>{dday}</td>'
                    f'<td><button class="hide-btn" onclick="hideRow(\'{pid}\')">숨기기</button></td></tr>'
                )
            block = (
                f'<h2>{title} ({len(posts)}건){new_badge}</h2>'
                f'<table><tr><th style="background:{color}">#</th>'
                f'<th style="background:{color}">제목</th>'
                f'<th style="background:{color}">접수</th>'
                f'<th style="background:{color}">D-day</th>'
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
  body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 40px auto; max-width: 1400px; padding: 0 40px; background: #f5f5f7; font-size: 16px; }}
  h1 {{ font-size: 28px; color: #1d1d1f; }}
  h2 {{ font-size: 21px; color: #1d1d1f; margin-top: 32px; }}
  .info {{ color: #86868b; margin-bottom: 20px; font-size: 15px; }}
  .new-badge {{ background: #ff3b30; color: white; font-size: 12px; padding: 2px 8px; border-radius: 10px; margin-left: 8px; }}
  .new-tag {{ background: #ff3b30; color: white; font-size: 11px; padding: 1px 6px; border-radius: 4px; }}
  .new-row td {{ background: #fff8f0; }}
  table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 24px; }}
  th {{ color: white; padding: 14px 16px; text-align: center; font-weight: 500; font-size: 15px; }}
  th:nth-child(2) {{ text-align: left; }}
  td {{ padding: 14px 16px; border-bottom: 1px solid #f0f0f0; text-align: center; }}
  td:nth-child(2) {{ text-align: left; }}
  td:nth-child(3) {{ white-space: nowrap; min-width: 180px; }}
  tr:hover td {{ background: #f0f7ff; }}
  a {{ color: #0071e3; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  .empty {{ text-align: center; padding: 40px; color: #86868b; }}
  .dday {{ font-size: 13px; font-weight: 600; color: #34a853; white-space: nowrap; }}
  .dday.soon {{ color: #ff9500; }}
  .dday.urgent {{ color: #ff3b30; font-weight: 700; }}
  .dday.expired {{ color: #86868b; font-weight: 400; text-decoration: line-through; }}
  .hide-btn {{ background: none; border: 1px solid #ccc; color: #86868b; font-size: 12px; padding: 4px 10px; border-radius: 6px; cursor: pointer; white-space: nowrap; }}
  .hide-btn:hover {{ background: #ff3b30; color: white; border-color: #ff3b30; }}
  .hidden-row {{ display: none; }}
  .footer {{ margin-top: 40px; padding: 16px 0; color: rgba(0,0,0,0.3); font-size: 12px; text-align: center; }}
  .reset-btn {{ background: none; border: 1px solid #ccc; color: #86868b; font-size: 12px; padding: 4px 12px; border-radius: 6px; cursor: pointer; margin-left: 12px; }}
  .reset-btn:hover {{ background: #0071e3; color: white; border-color: #0071e3; }}
</style>
</head>
<body>
<h1>공고 모니터링 <button class="reset-btn" onclick="resetHidden()">숨김 초기화</button></h1>
<p class="info">{today} 기준 | 누적 {total}건{new_info}</p>
{"".join(body_parts)}
<div class="footer">파싱 시각: {today}</div>
<script>
const STORAGE_KEY = 'jobpost-hidden';
function getHidden() {{
  try {{ return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'); }}
  catch {{ return []; }}
}}
function saveHidden(ids) {{
  localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
}}
function renumber() {{
  document.querySelectorAll('table').forEach(table => {{
    let n = 1;
    table.querySelectorAll('tr').forEach(tr => {{
      if (tr.querySelector('th') || tr.classList.contains('hidden-row')) return;
      const td = tr.querySelector('td');
      if (td) td.textContent = n++;
    }});
  }});
}}
function hideRow(id) {{
  const hidden = getHidden();
  if (!hidden.includes(id)) {{ hidden.push(id); saveHidden(hidden); }}
  const row = document.getElementById('row-' + id);
  if (row) row.classList.add('hidden-row');
  renumber();
}}
function resetHidden() {{
  localStorage.removeItem(STORAGE_KEY);
  document.querySelectorAll('.hidden-row').forEach(r => r.classList.remove('hidden-row'));
  renumber();
}}
// 페이지 로드 시 숨긴 항목 적용
getHidden().forEach(id => {{
  const row = document.getElementById('row-' + id);
  if (row) row.classList.add('hidden-row');
}});
renumber();
</script>
</body>
</html>"""

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    if auto_open:
        subprocess.run(["open", str(html_path)], check=False)
