@echo off
title Installing Intelligent Learning Agent...
echo.
echo ============================================
echo   Intelligent Learning Agent - Installer
echo ============================================
echo.
echo This will install the app via WSL.
echo Make sure WSL is installed and Python is available.
echo.
echo Checking WSL...
wsl.exe --status >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: WSL not found. Please install WSL first:
    echo   wsl --install
    pause
    exit /b 1
)
echo WSL detected.
echo.

REM Get current directory as WSL path
for /f "delims=" %%i in ('wsl.exe wslpath "%CD%"') do set WSL_PATH=%%i

echo Installing from: %WSL_PATH%
echo.
wsl.exe -e bash -lc "cd '%WSL_PATH%' && bash install.sh no"
echo.
echo ============================================
echo   Installation complete!
echo ============================================
echo.
echo Next steps:
echo   1. Edit backend\.env and add your DeepSeek API key
echo   2. Double-click this file to start: 启动智能学习Agent.bat
echo.
pause
