#!/usr/bin/env python3
"""하이브레인넷 채용공고 + NRF 신규과제 모니터링 봇"""

import sys

from common import log, send_notifications, open_summary
import hibrain
import nrf


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

    # HTML 요약 (하나라도 있으면)
    if hibrain_new or nrf_new:
        open_summary([
            ("하이브레인 채용공고", "#0071e3", hibrain_new),
            ("NRF 신규사업공모", "#34a853", nrf_new),
        ])
        log(f"총 {len(hibrain_new) + len(nrf_new)}건 알림 완료")
    else:
        log("새 공고 없음")


if __name__ == "__main__":
    main()
