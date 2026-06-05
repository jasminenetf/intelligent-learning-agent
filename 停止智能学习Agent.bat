@echo off
title Stopping Intelligent Learning Agent...
echo Stopping Intelligent Learning Agent...
echo.

set "BAT_DIR=%~dp0"
set "BAT_DIR=%BAT_DIR:~0,-1%"
for /f "delims=" %%i in ('wsl.exe wslpath "%BAT_DIR%"') do set WSL_PATH=%%i

wsl.exe -e bash -lc "cd '%WSL_PATH%' && bash scripts/stop_app.sh"
echo.
pause
