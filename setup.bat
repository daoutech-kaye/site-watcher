@echo off
REM Windows 설치 스크립트
cd /d "%~dp0"
echo 1/3 가상환경 생성...
python -m venv venv
call venv\Scripts\activate
echo 2/3 라이브러리 설치...
python -m pip install --upgrade pip
pip install -r requirements.txt
echo 3/3 브라우저(Chromium) 설치...
playwright install chromium
echo.
echo 설치 완료! 이제 run.bat 을 더블클릭해서 실행하세요.
pause
