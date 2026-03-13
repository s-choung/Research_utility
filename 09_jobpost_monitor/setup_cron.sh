#!/bin/bash
# 하이브레인넷 모니터링 cron 설정 스크립트

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_PYTHON="${SCRIPT_DIR}/venv/bin/python3"
MONITOR_SCRIPT="${SCRIPT_DIR}/monitor.py"

# 기본: 30분마다 실행
INTERVAL="${1:-30}"

echo "=== 하이브레인넷 모니터링 cron 설정 ==="
echo "스크립트 경로: ${MONITOR_SCRIPT}"
echo "Python 경로: ${VENV_PYTHON}"
echo "체크 간격: ${INTERVAL}분마다"
echo ""

# cron 표현식 생성
if [ "$INTERVAL" -eq 30 ]; then
    CRON_EXPR="*/30 * * * *"
elif [ "$INTERVAL" -eq 60 ]; then
    CRON_EXPR="0 * * * *"
elif [ "$INTERVAL" -le 59 ]; then
    CRON_EXPR="*/${INTERVAL} * * * *"
else
    echo "ERROR: 1~60분 사이의 값을 입력하세요"
    exit 1
fi

CRON_LINE="${CRON_EXPR} ${VENV_PYTHON} ${MONITOR_SCRIPT} --all >> ${SCRIPT_DIR}/cron.log 2>&1"

echo "추가할 cron 항목:"
echo "  ${CRON_LINE}"
echo ""

read -p "cron에 추가하시겠습니까? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # 기존 hibrain 관련 cron 제거 후 새로 추가
    (crontab -l 2>/dev/null | grep -v "monitor.py" ; echo "${CRON_LINE}") | crontab -
    echo "cron 등록 완료!"
    echo ""
    echo "현재 cron 목록:"
    crontab -l
    echo ""
    echo "=== 유용한 명령어 ==="
    echo "로그 확인:    tail -f ${SCRIPT_DIR}/monitor.log"
    echo "cron 로그:    tail -f ${SCRIPT_DIR}/cron.log"
    echo "cron 삭제:    crontab -l | grep -v 'monitor.py' | crontab -"
    echo "수동 실행:    ${VENV_PYTHON} ${MONITOR_SCRIPT} --all"
else
    echo "취소되었습니다."
    echo ""
    echo "수동으로 추가하려면:"
    echo "  crontab -e"
    echo "  아래 줄 추가:"
    echo "  ${CRON_LINE}"
fi
