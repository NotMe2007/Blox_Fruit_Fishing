@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

echo.
echo ========================================
echo   PYTHON VERSION TEST
echo ========================================
echo.

cd /d "%~dp0"

:: Check Python
python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo ✅ Python is installed
    python --version
) else (
    echo ❌ Python not found
    pause
    exit /b 1
)

:: Get Python version and check it
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set "PYTHON_VERSION=%%i"
echo Python version detected: %PYTHON_VERSION%

:: Extract major and minor version numbers
for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
    set "MAJOR_VERSION=%%a"
    set "MINOR_VERSION=%%b"
)

echo Major version: %MAJOR_VERSION%
echo Minor version: %MINOR_VERSION%

:: Check if version is 3.8 or higher
if %MAJOR_VERSION% LSS 3 (
    echo ❌ Python version is too old (need 3.8+)
    pause
    exit /b 1
)
if %MAJOR_VERSION% EQU 3 (
    if %MINOR_VERSION% LSS 8 (
        echo ❌ Python version is too old (need 3.8+)
        pause
        exit /b 1
    )
)

echo ✅ Python version is compatible (3.8+)
echo.
echo Test completed successfully!
pause