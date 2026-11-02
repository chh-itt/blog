@echo off
setlocal
title Blog System - Start All
echo ============================================
echo   Zhibo Space - Personal Blog CMS
echo   One-Click Start (Redis + Django + Celery + Vue)
echo ============================================
echo.

REM ===== Root dir = this script's folder (D:\...\blog-project) =====
set "ROOT=%~dp0"
set "BACKEND_DIR=%ROOT%backend"
set "FRONTEND_DIR=%ROOT%frontend"
set "REDIS_DIR=D:\environment\redis\extracted\Redis-8.10.1-Windows-x64-msys2"

REM ===== 1. Redis (portable msys2 build MUST run from its own folder, use RELATIVE path for config: absolute D:\ paths get mangled by msys2 path conversion) =====
echo [1/4] Checking Redis ...
tasklist /FI "IMAGENAME eq redis-server.exe" 2>nul | find /I "redis-server.exe" >nul
if %errorlevel%==0 (
    echo       Redis already running (port 6379)
) else (
    start "Redis-Server" /D "%REDIS_DIR%" "%REDIS_DIR%\redis-server.exe" .\redis.conf
    echo       Redis started (port 6379, password blog123456)
)

REM ===== 2. Django backend (port 8100) =====
echo [2/4] Starting Django backend ...
start "Django-Backend" /D "%BACKEND_DIR%" cmd /c ""%BACKEND_DIR%\.venv\Scripts\python.exe" "%BACKEND_DIR%\manage.py" runserver 127.0.0.1:8100 --noreload"
echo       Backend URL: http://127.0.0.1:8100/api/health/

REM ===== 3. Celery worker (optional) =====
echo [3/4] Starting Celery worker ...
start "Celery-Worker" /D "%BACKEND_DIR%" cmd /c ""%BACKEND_DIR%\.venv\Scripts\python.exe" -m celery -A config worker --pool=solo --loglevel=info"
echo       Celery worker started

REM ===== 4. Vue frontend (port 5173) =====
echo [4/4] Starting frontend ...
start "Frontend-Vite" /D "%FRONTEND_DIR%" cmd /k "npm run dev"
echo       Frontend URL: http://localhost:5173/

echo.
echo ============================================
echo  All services started! Open http://localhost:5173/
echo  Admin account: admin / admin123456
echo  Demo user:     testuser / test123456
echo ============================================
timeout /t 3 >nul 2>nul || ping -n 4 127.0.0.1 >nul
