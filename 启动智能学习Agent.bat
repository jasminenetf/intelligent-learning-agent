@echo off
setlocal EnableExtensions EnableDelayedExpansion
title 智学工坊 - 一键启动器

chcp 65001 >nul
color 0A

echo ==============================================
echo   智学工坊 - 一键启动器
echo ==============================================
echo.

REM 获取启动器所在目录（项目根目录）
set "ROOT_DIR=%~dp0"
if "%ROOT_DIR:~-1%"=="\" set "ROOT_DIR=%ROOT_DIR:~0,-1%"

if not exist "%ROOT_DIR%\backend" (
  echo [错误] 未找到 backend 目录，请确认启动器放在项目根目录中。
  echo 当前目录：%ROOT_DIR%
  pause
  exit /b 1
)

if not exist "%ROOT_DIR%\frontend-demo" (
  echo [错误] 未找到 frontend-demo 目录，请确认项目结构完整。
  echo 当前目录：%ROOT_DIR%
  pause
  exit /b 1
)

where wsl.exe >nul 2>nul
if errorlevel 1 (
  echo [错误] 未找到 WSL。请先安装并启用 WSL 后再启动。
  echo 参考：wsl --install
  pause
  exit /b 1
)

echo [1/4] 检查 WSL 环境...
for /f "delims=" %%i in ('wsl.exe wslpath "%ROOT_DIR%"') do set "WSL_PATH=%%i"
if not defined WSL_PATH (
  echo [错误] 无法转换项目路径到 WSL 路径。
  pause
  exit /b 1
)

echo [2/4] 启动后端和前端服务...
echo       项目路径：%ROOT_DIR%
echo       WSL 路径  ：%WSL_PATH%
echo.

start "智学工坊服务" /min wsl.exe -e bash -lc "cd '%WSL_PATH%' && bash scripts/start_app.sh > /tmp/zhixue_start.log 2>&1"

echo [3/4] 等待服务启动...
ping 127.0.0.1 -n 6 >nul

echo [4/4] 打开浏览器...
start "" http://127.0.0.1:5173

echo.
echo 启动完成。
echo 如果浏览器没有自动打开，请手动访问：
echo http://127.0.0.1:5173
echo.
echo 提示：
echo - 关闭窗口不会停止服务
necho - 如需停止服务，请运行“停止智能学习Agent.bat”
echo.
pause
endlocal
