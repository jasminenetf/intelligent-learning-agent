@echo off
setlocal
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8010" ^| findstr "LISTENING"') do taskkill /F /PID %%p >nul 2>nul
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do taskkill /F /PID %%p >nul 2>nul
endlocal
