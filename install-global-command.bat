@echo off
echo Installing global 'cfc-reload' command...
echo.

REM Get the current directory
set "SCRIPT_DIR=%~dp0"

REM Create a global batch file in System32 (requires admin) or suggest user PATH
set "GLOBAL_SCRIPT=%WINDIR%\System32\cfc-reload.bat"

REM Try to create global command (requires admin rights)
echo @echo off > "%GLOBAL_SCRIPT%" 2>nul
echo cd /d "%SCRIPT_DIR%" >> "%GLOBAL_SCRIPT%" 2>nul
echo cfc-reload.bat >> "%GLOBAL_SCRIPT%" 2>nul

if %ERRORLEVEL% EQU 0 (
    echo ✅ Global command installed successfully!
    echo    You can now run 'cfc-reload' from anywhere
) else (
    echo ❌ Could not install global command (admin rights required)
    echo.
    echo ALTERNATIVE SETUP:
    echo 1. Add this folder to your PATH environment variable:
    echo    %SCRIPT_DIR%
    echo.
    echo 2. Or create an alias in your shell:
    echo    doskey cfc-reload=cd /d "%SCRIPT_DIR%" ^& cfc-reload.bat
    echo.
    echo 3. Or simply run from this directory:
    echo    cfc-reload
)

echo.
pause