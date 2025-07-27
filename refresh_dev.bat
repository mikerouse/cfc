@echo off
echo Refreshing development environment...

REM Kill any existing Python processes
echo Stopping existing Django server...
powershell -Command "Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force"

REM Wait a moment for processes to fully stop
timeout /t 2 >nul

REM Clear Django cache if it exists
if exist "__pycache__" (
    echo Clearing Python cache...
    for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
)

REM Clear browser cache files that might be served by Django
if exist "static\CACHE" (
    echo Clearing static cache...
    rd /s /q "static\CACHE"
)

REM Run Django checks
echo Running Django checks...
python manage.py check

REM Start development server
echo Starting Django development server...
echo.
echo Development server will start on http://127.0.0.1:8000/
echo Press Ctrl+C to stop the server
echo.
python manage.py runserver