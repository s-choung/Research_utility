#!/bin/bash
# 채용공고/NRF 모니터링 로컬 설정 스크립트
# 사용법: bash setup.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"

echo "=== Jobpost Monitor Setup ==="

# venv 생성
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    echo "venv 생성 완료"
fi

# 패키지 설치
"$VENV_DIR/bin/pip" install -q -r "$SCRIPT_DIR/requirements.txt"
echo "패키지 설치 완료"

# 초기화 (기존 공고 기록)
"$VENV_DIR/bin/python3" "$SCRIPT_DIR/monitor.py" --init
echo ""
echo "=== 설정 완료 ==="
echo "수동 실행: $VENV_DIR/bin/python3 $SCRIPT_DIR/monitor.py --all"
