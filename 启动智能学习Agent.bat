@echo off
setlocal EnableExtensions
title Smart Learning Agent Launcher

set "ROOT_DIR=%~dp0"
if "%ROOT_DIR:~-1%"=="\" set "ROOT_DIR=%ROOT_DIR:~0,-1%"
set "BACKEND_DIR=%ROOT_DIR%\backend"
set "FRONTEND_DIR=%ROOT_DIR%\frontend-demo"
set "APP_URL=http://127.0.0.1:5173"

echo ========================================
echo Smart Learning Agent One Click Launcher
echo ========================================
echo Project: %ROOT_DIR%
echo Backend: %BACKEND_DIR%
echo Frontend: %FRONTEND_DIR%
echo.

if not exist "%BACKEND_DIR%" (
  echo [ERROR] Backend folder not found: %BACKEND_DIR%
  pause
  exit /b 1
)
if not exist "%FRONTEND_DIR%" (
  echo [ERROR] Frontend folder not found: %FRONTEND_DIR%
  pause
  exit /b 1
)
where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python was not found in PATH.
  pause
  exit /b 1
)

echo [1/4] Starting services on stable demo ports...
echo Backend API: http://127.0.0.1:8010
echo Cleaning old listeners on 8010 and 5173...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8010" ^| findstr "LISTENING"') do taskkill /F /PID %%p >nul 2>nul
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do taskkill /F /PID %%p >nul 2>nul
timeout /t 1 /nobreak >nul

echo [2/4] Starting backend...
start "SmartLearning-Backend" /D "%BACKEND_DIR%" cmd /k "python -m uvicorn app.demo_main:app --host 127.0.0.1 --port 8010"

echo [3/4] Starting frontend...
start "SmartLearning-Frontend" /D "%FRONTEND_DIR%" cmd /k "python -m http.server 5173 --bind 127.0.0.1"

echo [4/5] Waiting for backend health check...
timeout /t 4 /nobreak >nul
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8010/health' -UseBasicParsing -TimeoutSec 8; if ($r.StatusCode -ne 200) { exit 1 } } catch { exit 1 }" >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Backend health check failed: http://127.0.0.1:8010/health
  echo Please check the SmartLearning-Backend window for Python dependency or startup errors.
  pause
  exit /b 1
)

echo [5/5] Opening browser...
start "" "%APP_URL%"
if errorlevel 1 explorer "%APP_URL%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process '%APP_URL%'" >nul 2>nul

echo.
echo Launcher finished.
echo If the browser did not open, copy this URL into your browser:
echo %APP_URL%
echo.
echo Keep the Backend and Frontend windows open.
echo.
pause
endlocal
