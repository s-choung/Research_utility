#!/bin/bash
# 하이브레인넷 모니터링 launchd 설정 스크립트
# launchd는 macOS 기본 스케줄러로, cron보다 안정적이며
# 잠자기 후 깨어나면 놓친 스케줄을 자동 실행합니다.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_PYTHON="${SCRIPT_DIR}/venv/bin/python3"
MONITOR_SCRIPT="${SCRIPT_DIR}/monitor.py"
PLIST_NAME="com.sean.hibrain-monitor"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_NAME}.plist"

echo "=== 하이브레인넷 모니터링 launchd 설정 ==="
echo "스크립트: ${MONITOR_SCRIPT}"
echo "Python:   ${VENV_PYTHON}"
echo "plist:    ${PLIST_PATH}"
echo ""

# LaunchAgents 디렉토리 확인
mkdir -p "$HOME/Library/LaunchAgents"

cat > "${PLIST_PATH}" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_NAME}</string>

    <key>ProgramArguments</key>
    <array>
        <string>${VENV_PYTHON}</string>
        <string>${MONITOR_SCRIPT}</string>
        <string>--all</string>
    </array>

    <!-- 매일 오전 9시에 실행 -->
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

    <!-- 로그 파일 -->
    <key>StandardOutPath</key>
    <string>${SCRIPT_DIR}/launchd_stdout.log</string>
    <key>StandardErrorPath</key>
    <string>${SCRIPT_DIR}/launchd_stderr.log</string>

    <!-- 작업 디렉토리 -->
    <key>WorkingDirectory</key>
    <string>${SCRIPT_DIR}</string>

    <!-- 네트워크 필요 -->
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
PLIST

echo "plist 파일 생성 완료"
echo ""

# 기존 등록 해제 (있다면)
launchctl bootout "gui/$(id -u)/${PLIST_NAME}" 2>/dev/null

# 새로 등록
launchctl bootstrap "gui/$(id -u)" "${PLIST_PATH}"

if [ $? -eq 0 ]; then
    echo "launchd 등록 완료!"
else
    echo "launchd 등록 실패. 수동으로 등록하세요:"
    echo "  launchctl load ${PLIST_PATH}"
fi

echo ""
echo "=== 상태 확인 ==="
launchctl print "gui/$(id -u)/${PLIST_NAME}" 2>&1 | head -5
echo ""
echo "=== 유용한 명령어 ==="
echo "상태 확인:     launchctl print gui/$(id -u)/${PLIST_NAME}"
echo "수동 실행:     launchctl kickstart gui/$(id -u)/${PLIST_NAME}"
echo "등록 해제:     launchctl bootout gui/$(id -u)/${PLIST_NAME}"
echo "로그 확인:     tail -f ${SCRIPT_DIR}/monitor.log"
echo "수동 테스트:   ${VENV_PYTHON} ${MONITOR_SCRIPT} --all"
