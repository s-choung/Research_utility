#!/usr/bin/env python3
"""하이브레인넷 채용공고 + NRF 신규과제 모니터링 봇"""

import sys

from common import log, send_notifications, open_summary, load_json, save_json, SCRIPT_DIR
import hibrain
import nrf

HISTORY_FILE = SCRIPT_DIR / "matched_history.json"
HIDDEN_FILE = SCRIPT_DIR / "hidden_posts.json"


def load_hidden() -> set[str]:
    if HIDDEN_FILE.exists():
        import json
        return set(json.loads(HIDDEN_FILE.read_text("utf-8")))
    return set()


def load_history() -> list[dict]:
    data = load_json(HISTORY_FILE)
    return data.get("hibrain", []), data.get("nrf", [])


def save_history(hibrain_posts, nrf_posts):
    save_json(HISTORY_FILE, {"hibrain": hibrain_posts, "nrf": nrf_posts})


def merge_posts(existing: list[dict], new: list[dict]) -> list[dict]:
    """새 공고를 기존 목록에 추가 (중복 제거, 최신이 위)"""
    seen_ids = {p["id"] for p in existing}
    merged = list(new)  # 새 공고 먼저
    for p in existing:
        if p["id"] not in {n["id"] for n in new}:
            merged.append(p)
    return merged


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--init":
        log("초기화 모드: 기존 공고를 기록합니다...")
        hibrain.init()
        nrf.init()
        return

    # 하이브레인 채용공고
    hibrain_new = hibrain.check_new()

    # NRF 신규사업공모
    nrf_new = nrf.check_new()

    # 알림 발송
    if hibrain_new:
        send_notifications(hibrain_new, "하이브레인")
    if nrf_new:
        send_notifications(nrf_new, "NRF")

    # 누적 히스토리 업데이트
    hist_hibrain, hist_nrf = load_history()
    hist_hibrain = merge_posts(hist_hibrain, hibrain_new)
    hist_nrf = merge_posts(hist_nrf, nrf_new)
    save_history(hist_hibrain, hist_nrf)

    # 숨긴 공고 필터링
    hidden = load_hidden()
    show_hibrain = [p for p in hist_hibrain if p["id"] not in hidden]
    show_nrf = [p for p in hist_nrf if p["id"] not in hidden]

    # HTML 요약 (누적 데이터 표시, 새 공고 수 표기)
    open_summary(
        sections=[
            ("하이브레인 채용공고", "#0071e3", show_hibrain, len(hibrain_new)),
            ("NRF 신규사업공모", "#34a853", show_nrf, len(nrf_new)),
        ],
        auto_open="--open" in sys.argv,
    )

    total = len(hibrain_new) + len(nrf_new)
    if total:
        log(f"새 공고 {total}건 (누적: 하이브레인 {len(hist_hibrain)}, NRF {len(hist_nrf)})")
    else:
        log(f"새 공고 없음 (누적: 하이브레인 {len(hist_hibrain)}, NRF {len(hist_nrf)})")


if __name__ == "__main__":
    main()
