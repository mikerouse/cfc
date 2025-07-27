@echo off
echo Council Finance Counters - Development Reload
echo =============================================

REM Kill any existing Python processes
echo [1/4] Stopping Django server...
powershell -Command "Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force" >nul 2>&1

REM Wait for processes to stop
timeout /t 2 >nul

REM Clear Django cache
echo [2/4] Clearing caches...
python manage.py clear_dev_cache >nul 2>&1

REM Run Django checks
echo [3/4] Running checks...
python manage.py check

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ Django checks failed! Please fix the errors above before starting the server.
    pause
    exit /b 1
)

REM Start development server
echo [4/4] Starting development server...
echo.
echo ✅ CFC development server starting...
echo    Navigate to: http://127.0.0.1:8000/
echo    Press Ctrl+C to stop
echo.
python manage.py runserver