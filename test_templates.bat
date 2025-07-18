@echo off
REM Template Testing Script for Windows
REM Usage: test_templates.bat [template_name]

echo.
echo 🧪 Django Template Syntax Checker
echo ===================================

if "%1"=="" (
    echo Checking all templates...
    python check_templates.py
) else (
    echo Checking template: %1
    python check_templates.py %1
)

echo.
pause
