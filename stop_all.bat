@echo off
setlocal
title Blog System - Stop All
echo Stopping blog system processes...
echo.

echo [1/4] Stopping frontend (node/vite, port 5173) ...
taskkill /F /FI "WINDOWTITLE eq Frontend-Vite*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq *vite*" >nul 2>&1
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":5173 " ^| findstr "LISTENING"') do (
    taskkill /F /PID %%p >nul 2>&1
)

echo [2/4] Stopping Django backend ...
taskkill /F /FI "WINDOWTITLE eq Django-Backend*" >nul 2>&1
for /f "tokens=2" %%p in ('tasklist /FI "IMAGENAME eq python.exe" /FO LIST ^| find "PID"') do (
    taskkill /F /PID %%p >nul 2>&1
)

echo [3/4] Stopping Celery ...
taskkill /F /FI "WINDOWTITLE eq Celery-Worker*" >nul 2>&1

echo [4/4] Stopping Redis ...
taskkill /F /IM redis-server.exe >nul 2>&1

echo.
echo All stopped.
timeout /t 2 >nul 2>nul || ping -n 3 127.0.0.1 >nul
