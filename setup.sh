#!/usr/bin/env bash
# Mac / Linux 설치 스크립트
set -e
cd "$(dirname "$0")"
echo "1/3 가상환경 생성..."
python3 -m venv venv
source venv/bin/activate
echo "2/3 라이브러리 설치..."
pip install --upgrade pip >/dev/null
pip install -r requirements.txt
echo "3/3 브라우저(Chromium) 설치..."
playwright install chromium
echo ""
echo "✅ 설치 완료! 이제 ./run.sh 로 실행하세요."
