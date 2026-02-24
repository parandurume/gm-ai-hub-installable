@echo off
REM GM-AI-Hub 관공서 PC 설치 스크립트 (RULE-10: 멱등성 보장)
REM 사용법: scripts\install_govpc.bat [설치_경로]

setlocal enabledelayedexpansion

set "INSTALL_DIR=%~1"
if "%INSTALL_DIR%"=="" set "INSTALL_DIR=%USERPROFILE%\GM-AI-Hub"

echo ===================================
echo  GM-AI-Hub 관공서 PC 설치
echo ===================================
echo.
echo 설치 경로: %INSTALL_DIR%

REM 1. 설치 디렉토리 생성 (멱등: 이미 존재해도 OK)
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

REM 2. Python 확인
echo.
echo [1/6] Python 확인...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python이 설치되어 있지 않습니다.
    echo Python 3.11 이상을 설치해 주세요.
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo Python %PYVER% 확인됨

REM 3. 파일 복사
echo.
echo [2/6] 파일 복사...
set "SCRIPT_DIR=%~dp0"
set "USB_DIR=%SCRIPT_DIR%.."

xcopy /E /Y /I "%USB_DIR%\backend" "%INSTALL_DIR%\backend" >nul 2>&1
xcopy /E /Y /I "%USB_DIR%\mcp_server" "%INSTALL_DIR%\mcp_server" >nul 2>&1
xcopy /E /Y /I "%USB_DIR%\data" "%INSTALL_DIR%\data" >nul 2>&1
xcopy /E /Y /I "%USB_DIR%\frontend" "%INSTALL_DIR%\frontend" >nul 2>&1
xcopy /E /Y /I "%USB_DIR%\scripts" "%INSTALL_DIR%\scripts" >nul 2>&1
copy /Y "%USB_DIR%\pyproject.toml" "%INSTALL_DIR%\" >nul 2>&1

REM 4. .env 설정 (멱등: 이미 존재하면 덮어쓰지 않음)
echo.
echo [3/6] 환경 설정...
if not exist "%INSTALL_DIR%\.env" (
    copy "%USB_DIR%\.env.example" "%INSTALL_DIR%\.env" >nul 2>&1
    echo .env 파일이 생성되었습니다. 필요시 수정하세요.
) else (
    echo .env 파일이 이미 존재합니다. 기존 설정을 유지합니다.
)

REM 5. Python 가상환경 + 패키지 설치
echo.
echo [4/6] Python 가상환경 설정...
if not exist "%INSTALL_DIR%\.venv" (
    python -m venv "%INSTALL_DIR%\.venv"
    echo 가상환경 생성 완료
) else (
    echo 가상환경이 이미 존재합니다.
)

echo.
echo [5/6] Python 패키지 설치...
call "%INSTALL_DIR%\.venv\Scripts\activate.bat"

REM 오프라인 설치 시도 (USB 패키지 내 packages 폴더)
if exist "%USB_DIR%\packages" (
    pip install --no-index --find-links="%USB_DIR%\packages" -e "%INSTALL_DIR%" >nul 2>&1
    if errorlevel 1 (
        echo 오프라인 설치 실패. 온라인 설치를 시도합니다...
        pip install -e "%INSTALL_DIR%" >nul 2>&1
    )
) else (
    pip install -e "%INSTALL_DIR%" >nul 2>&1
)
echo 패키지 설치 완료

REM 6. 작업 디렉토리 생성
echo.
echo [6/6] 작업 디렉토리 생성...
if not exist "%INSTALL_DIR%\working_docs" mkdir "%INSTALL_DIR%\working_docs"
if not exist "%INSTALL_DIR%\working_docs\import" mkdir "%INSTALL_DIR%\working_docs\import"
if not exist "%INSTALL_DIR%\working_docs\export" mkdir "%INSTALL_DIR%\working_docs\export"
if not exist "%INSTALL_DIR%\db" mkdir "%INSTALL_DIR%\db"

REM 7. 바로가기 생성
echo.
echo 바탕화면 바로가기 생성...
set "DESKTOP=%USERPROFILE%\Desktop"
(
echo @echo off
echo cd /d "%INSTALL_DIR%"
echo call .venv\Scripts\activate.bat
echo echo GM-AI-Hub 서버를 시작합니다...
echo echo 브라우저에서 http://localhost:8080 을 열어주세요.
echo python -m uvicorn backend.main:app --host 127.0.0.1 --port 8080
echo pause
) > "%DESKTOP%\GM-AI-Hub 시작.bat"

echo.
echo ===================================
echo  설치 완료!
echo ===================================
echo.
echo 사용법:
echo   1. 바탕화면의 "GM-AI-Hub 시작.bat"을 실행하세요
echo   2. 브라우저에서 http://localhost:8080 접속
echo   3. Ollama가 필요합니다 (별도 설치)
echo.
echo Ollama 설치:
echo   - https://ollama.com/download 에서 다운로드
echo   - 또는 USB의 ollama-setup.exe 실행 (포함된 경우)
echo   - 설치 후: ollama pull gpt-oss:20b
echo.

pause
