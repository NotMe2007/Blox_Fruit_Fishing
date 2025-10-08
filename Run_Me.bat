@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

:: =============================================================================
:: Blox Fruit Fishing - Automated Setup and Launch Script
:: =============================================================================
:: This script will:
:: 1. Check for Python installation (install if missing)
:: 2. Check and install requirements.txt dependencies
:: 3. Run quick tests to verify system health
:: 4. Launch Main.py if tests pass or contact support if major issues
:: =============================================================================

echo.
echo ========================================
echo   BLOX FRUIT FISHING - AUTO LAUNCHER
echo ========================================
echo.

:: Change to script directory
cd /d "%~dp0"

:: Create a simple backup of this script before modifying behavior
if not exist "Run_Me.bat.bak" copy "%~f0" "Run_Me.bat.bak" >nul 2>&1

:: Check if a newer release is available before continuing the setup
call :CHECK_FOR_UPDATES

:: =============================================================================
:: STEP 1: CHECK PYTHON INSTALLATION
:: =============================================================================
echo [STEP 1] Checking Python installation...

:: Try to find Python
python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo ✅ Python is installed
    python --version
) else (
    echo ❌ Python not found in PATH
    echo.
    echo Checking for Python in common locations...
    
    :: Check common Python installation paths
    set "PYTHON_FOUND="
    for %%p in (
        "C:\Python3*\python.exe"
        "C:\Program Files\Python3*\python.exe"
        "C:\Program Files (x86)\Python3*\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python3*\python.exe"
        "%APPDATA%\Local\Programs\Python\Python3*\python.exe"
    ) do (
        if exist "%%p" (
            set "PYTHON_FOUND=%%p"
            goto :python_found
        )
    )
    
    :python_not_found
    echo.
    echo 🔽 Python not found! Attempting to install Python...
    echo.
    echo Opening Microsoft Store to install Python...
    echo Please install Python 3.8 or higher from the Microsoft Store
    echo.
    start ms-windows-store://pdp/?ProductId=9NRWMJP3717K
    echo.
    echo After installing Python:
    echo 1. Close this window
    echo 2. Run this script again
    echo.
    pause
    exit /b 1
    
    :python_found
    echo ✅ Found Python at: !PYTHON_FOUND!
    set "PYTHON_CMD=!PYTHON_FOUND!"
    goto :check_version
)

set "PYTHON_CMD=python"

:check_version
echo.
echo [STEP 1.5] Checking Python version...

:: Get Python version and check it
for /f "tokens=2" %%i in ('%PYTHON_CMD% --version 2^>^&1') do set "PYTHON_VERSION=%%i"
echo Python version detected: %PYTHON_VERSION%

:: Extract major and minor version numbers
for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
    set "MAJOR_VERSION=%%a"
    set "MINOR_VERSION=%%b"
)

:: Check if version is 3.8 or higher
if %MAJOR_VERSION% LSS 3 (
    goto :version_too_old
)
if %MAJOR_VERSION% EQU 3 (
    if %MINOR_VERSION% LSS 8 (
        goto :version_too_old
    )
)

echo ✅ Python version is compatible
goto :check_venv

:version_too_old
echo ❌ Python version is too old (need 3.8+)
echo Current version: %PYTHON_VERSION%
echo Please install Python 3.8 or higher
pause
exit /b 1

:check_venv

:: =============================================================================
:: STEP 2: CHECK VIRTUAL ENVIRONMENT
:: =============================================================================
echo.
echo [STEP 2] Checking virtual environment...

if exist ".venv\Scripts\python.exe" (
    echo ✅ Virtual environment found
    set "PYTHON_CMD=.venv\Scripts\python.exe"
    set "PIP_CMD=.venv\Scripts\pip.exe"
) else (
    echo ⚠️  No virtual environment found. Using system Python and pip for normal usage.
    :: Use the system python command resolved earlier and system pip
    set "PIP_CMD=pip"
    :: Do NOT attempt to create a virtual environment automatically to avoid failures on some systems
    echo Skipping automatic creation of .venv. If you want an isolated environment, create one manually with:
    echo    python -m venv .venv
    echo Then re-run this script.
)

:: =============================================================================
:: STEP 3: CHECK AND INSTALL REQUIREMENTS
:: =============================================================================
echo.
echo [STEP 3] Checking requirements...

if not exist "requirements.txt" (
    echo ❌ requirements.txt not found!
    echo Creating basic requirements.txt...
    
    echo opencv-python^>=4.8.0> requirements.txt
    echo numpy^>=1.21.0>> requirements.txt
    echo pillow^>=8.3.0>> requirements.txt
    echo psutil^>=5.8.0>> requirements.txt
    echo keyboard^>=0.13.5>> requirements.txt
    echo customtkinter^>=5.0.0>> requirements.txt
    echo pywin32^>=306>> requirements.txt
    
    echo ✅ Created basic requirements.txt
)

echo Installing/updating dependencies...
%PIP_CMD% install -r requirements.txt --upgrade
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Failed to install some dependencies
    echo Trying alternative installation methods...
    
    :: Try installing core packages individually
    echo Installing core packages...
    %PIP_CMD% install opencv-python numpy pillow
    if %ERRORLEVEL% NEQ 0 (
        echo ❌ Critical dependency installation failed
        echo.
        echo SOLUTION NEEDED:
        echo 1. Check your internet connection
        echo 2. Try running as Administrator
        echo 3. Contact support if issues persist
        echo.
        pause
        exit /b 1
    )
) else (
    echo ✅ All dependencies installed successfully
)

:: =============================================================================
:: STEP 4: RUN QUICK TESTS
:: =============================================================================
echo.
echo [STEP 4] Running system health check...

if not exist "tests\quick_test.py" (
    echo ❌ Test file not found: tests\quick_test.py
    echo Skipping tests and launching directly...
    goto :launch_main
)

echo Running quick diagnostic tests...
%PYTHON_CMD% tests\quick_test.py
set "TEST_RESULT=%ERRORLEVEL%"

echo.
if %TEST_RESULT% EQU 0 (
    echo ✅ ALL TESTS PASSED - System is ready!
    echo Launching Blox Fruit Fishing...
    goto :launch_main
) else (
    echo ⚠️  Some tests failed, checking severity...
    
    :: Count critical vs minor issues by running a simple check
    echo Analyzing test results...
    
    :: Check if critical components work by testing imports
    %PYTHON_CMD% -c "import cv2, numpy, PIL; print('CORE_OK')" >test_result.tmp 2>&1
    findstr "CORE_OK" test_result.tmp >nul
    if %ERRORLEVEL% EQU 0 (
        echo ✅ Core components working - Minor issues detected
        echo The system should still function with some limitations
        echo.
        set /p "CONTINUE=Continue anyway? (y/n): "
        if /i "!CONTINUE!"=="y" (
            goto :launch_main
        ) else (
            goto :contact_support
        )
    ) else (
        echo ❌ Critical component failure detected
        goto :contact_support
    )
)

:: =============================================================================
:: STEP 5: LAUNCH MAIN APPLICATION
:: =============================================================================
:launch_main
echo.
echo [STEP 5] Launching Blox Fruit Fishing...
echo.
echo 🎮 IMPORTANT INSTRUCTIONS:
echo 1. Make sure Roblox is running
echo 2. Join Blox Fruits game
echo 3. Go to a fishing area
echo 4. Use numpad keys to control the bot:
echo    - Numpad 1: Start fishing (default)
echo    - Numpad 2: Stop/Exit (default)
echo    - Adjust these hotkeys in the launcher under the "Hotkeys" tab if needed
echo.
echo Starting GUI...

if exist "Main.py" (
    %PYTHON_CMD% Main.py
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo ❌ Application crashed or failed to start
        echo Check the error messages above
        goto :contact_support
    )
) else (
    echo ❌ Main.py not found!
    goto :contact_support
)

echo.
echo Application closed normally
pause
exit /b 0

:: =============================================================================
:: SUBROUTINE: CHECK_FOR_UPDATES
:: =============================================================================
:CHECK_FOR_UPDATES
echo.
echo [STEP 0] Checking for updates...

set "REPO_OWNER=NotMe2007"
set "REPO_NAME=Blox_Fruit_Fishing"
set "VERSION_FILE=version.txt"
set "UPDATES_DIR=updates"

set "LOCAL_VERSION="
if exist "%VERSION_FILE%" (
    set /p LOCAL_VERSION=<"%VERSION_FILE%"
)
if not defined LOCAL_VERSION set "LOCAL_VERSION=unknown"

set "LATEST_VERSION="
set "LATEST_IS_PRERELEASE="
set "UPDATE_TMP=%TEMP%\bff_release.cmd"

del "%UPDATE_TMP%" >nul 2>&1
powershell -NoProfile -Command "$ErrorActionPreference='SilentlyContinue'; $headers=@{'User-Agent'='BloxFruitUpdater'}; $release=Invoke-RestMethod -UseBasicParsing -Headers $headers -Uri 'https://api.github.com/repos/%REPO_OWNER%/%REPO_NAME%/releases/latest'; if(-not $release){ $releases=Invoke-RestMethod -UseBasicParsing -Headers $headers -Uri 'https://api.github.com/repos/%REPO_OWNER%/%REPO_NAME%/releases?per_page=1'; if($releases){ if($releases -is [System.Collections.IEnumerable]){ $release=$releases | Select-Object -First 1 } else { $release=$releases } } }; if($release){ 'set LATEST_VERSION='+$release.tag_name; 'set LATEST_IS_PRERELEASE='+[string]$release.prerelease }" > "%UPDATE_TMP%"

if exist "%UPDATE_TMP%" (
    call "%UPDATE_TMP%"
    del "%UPDATE_TMP%" >nul 2>&1
)

if not defined LATEST_VERSION (
    echo ⚠️  Could not reach GitHub releases. Skipping update check.
    goto :EOF
)

echo    Local version: !LOCAL_VERSION!
echo    Latest release: !LATEST_VERSION!
if /I "!LATEST_IS_PRERELEASE!"=="True" (
    echo    Release type: pre-release
)

if /I "!LOCAL_VERSION!"=="!LATEST_VERSION!" goto :UPDATE_ALREADY_LATEST

echo ⚠️  Update available! Local version: !LOCAL_VERSION!  Latest version: !LATEST_VERSION!
if /I "!LATEST_IS_PRERELEASE!"=="True" (
    echo 📎 Note: This release is marked as a pre-release on GitHub.
)

if not exist "%UPDATES_DIR%" mkdir "%UPDATES_DIR%" >nul 2>&1

set "UPDATE_ARCHIVE=%UPDATES_DIR%\%REPO_NAME%_%LATEST_VERSION%.zip"
set "DOWNLOAD_URL=https://github.com/%REPO_OWNER%/%REPO_NAME%/archive/refs/tags/%LATEST_VERSION%.zip"
if exist "%UPDATE_ARCHIVE%" del "%UPDATE_ARCHIVE%" >nul 2>&1

"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -Command "@'
param(
    [string]$Url,
    [string]$Destination,
    [string]$UserAgent = 'BloxFruitUpdater'
)

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls13
$ErrorActionPreference = 'Stop'

$destDir = [System.IO.Path]::GetDirectoryName($Destination)
if (-not [string]::IsNullOrWhiteSpace($destDir) -and -not (Test-Path $destDir)) {
    New-Item -ItemType Directory -Path $destDir | Out-Null
}

$script:completed = $false
$script:errorMessage = $null
$wc = New-Object System.Net.WebClient
$wc.Headers['User-Agent'] = $UserAgent
$start = Get-Date

$wc.DownloadProgressChanged += {
    param($sender, $args)
    if ($args.TotalBytesToReceive -gt 0) {
        $percent = [int]$args.ProgressPercentage
        $receivedMB = $args.BytesReceived / 1MB
        $totalMB = $args.TotalBytesToReceive / 1MB
        $elapsed = (Get-Date) - $start
        $speedMBps = if ($elapsed.TotalSeconds -gt 0) { $args.BytesReceived / 1MB / $elapsed.TotalSeconds } else { 0 }
        $status = '{0}%% | {1:N1} MB / {2:N1} MB @ {3:N1} MB/s' -f $percent, $receivedMB, $totalMB, $speedMBps
        Write-Progress -Activity 'Downloading update' -Status $status -PercentComplete $percent
    } else {
        $status = '{0:N1} MB downloaded' -f ($args.BytesReceived / 1MB)
        Write-Progress -Activity 'Downloading update' -Status $status -PercentComplete 0
    }
}

$wc.DownloadFileCompleted += {
    param($sender, $args)
    if ($args.Error) {
        $script:errorMessage = $args.Error.Message
    }
    Write-Progress -Activity 'Downloading update' -Completed
    $script:completed = $true
}

try {
    $wc.DownloadFileAsync($Url, $Destination)
    while (-not $script:completed) {
        Start-Sleep -Milliseconds 200
    }
    if ($script:errorMessage) {
        throw $script:errorMessage
    }
    if (-not (Test-Path $Destination)) {
        throw 'Download failed - file not found.'
    }
    exit 0
}
catch {
    Write-Error $_
    exit 1
}
finally {
    if ($wc) { $wc.Dispose() }
}
'@ | Set-Content -Encoding UTF8 -Path '%DOWNLOAD_SCRIPT%'"

"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%DOWNLOAD_SCRIPT%" -Url "%DOWNLOAD_URL%" -Destination "%UPDATE_ARCHIVE%" || (
    if exist "%DOWNLOAD_SCRIPT%" del "%DOWNLOAD_SCRIPT%" >nul 2>&1
    if exist "%UPDATE_ARCHIVE%" del "%UPDATE_ARCHIVE%" >nul 2>&1
    echo ❌ Failed to download the latest release. Continuing without updating.
    goto :EOF
)

if exist "%DOWNLOAD_SCRIPT%" del "%DOWNLOAD_SCRIPT%" >nul 2>&1
echo ✅ Download complete. Extracting package...

set "EXTRACTED_FOLDER=%UPDATES_DIR%\%REPO_NAME%-%LATEST_VERSION%"
if exist "%EXTRACTED_FOLDER%" rd /s /q "%EXTRACTED_FOLDER%" >nul 2>&1

powershell -NoProfile -Command "try { Expand-Archive -LiteralPath '%UPDATE_ARCHIVE%' -DestinationPath '%UPDATES_DIR%' -Force } catch { exit 1 }"
if errorlevel 1 (
    echo ❌ Failed to extract the update package. Continuing without updating.
    del "%UPDATE_ARCHIVE%" >nul 2>&1
    goto :EOF
)

echo.
echo 📁 Latest version extracted to: %EXTRACTED_FOLDER%
echo.
set "TEST_DECISION="
set /p "TEST_DECISION=Would you like to test the new version before replacing the current install? (Y/N): "
if /I "%TEST_DECISION%"=="Y" (
    echo ✅ Keeping current installation. Test the update by running Run_Me.bat inside:
    echo    %EXTRACTED_FOLDER%
    echo Once satisfied, rerun this launcher to apply the update.
    del "%UPDATE_ARCHIVE%" >nul 2>&1
    goto :EOF
)

echo 🔄 Replacing current installation with version %LATEST_VERSION%...

robocopy "%EXTRACTED_FOLDER%" "%CD%" /E /R:1 /W:1 /NFL /NDL /NJH /NJS /NP /XD ".git" "%UPDATES_DIR%"
set "ROBO_EXIT=%ERRORLEVEL%"
if %ROBO_EXIT% GEQ 8 (
    echo ❌ Robocopy reported an error (code %ROBO_EXIT%). Update aborted.
    goto :EOF
)

echo %LATEST_VERSION%>"%VERSION_FILE%"
echo ✅ Update applied successfully.

if exist "%UPDATE_ARCHIVE%" del "%UPDATE_ARCHIVE%" >nul 2>&1
if exist "%EXTRACTED_FOLDER%" rd /s /q "%EXTRACTED_FOLDER%" >nul 2>&1

echo ℹ️  The launcher will now continue using the updated files.
goto :EOF

:UPDATE_ALREADY_LATEST
echo ✅ You already have the latest version (!LOCAL_VERSION!).
goto :EOF

:: =============================================================================
:: SUPPORT CONTACT SECTION
:: =============================================================================
:contact_support
echo.
echo ========================================
echo      TECHNICAL SUPPORT NEEDED
echo ========================================
echo.
echo ❌ Critical issues detected that prevent the application from running properly.
echo.
echo BEFORE CONTACTING SUPPORT, TRY THESE SOLUTIONS:
echo.
echo 1. RESTART AS ADMINISTRATOR:
echo    - Right-click this batch file
echo    - Select "Run as administrator"
echo    - Try again
echo.
echo 2. CHECK ANTIVIRUS SOFTWARE:
echo    - Temporarily disable antivirus
echo    - Add this folder to antivirus exclusions
echo    - Try running again
echo.
echo 3. UPDATE WINDOWS:
echo    - Install all Windows updates
echo    - Restart computer
echo    - Try again
echo.
echo 4. CLEAN INSTALLATION:
echo    - Delete .venv folder
echo    - Run this script again
echo.
echo IF PROBLEMS PERSIST:
echo.
echo 📧 Contact Support:
echo    - Create an issue on GitHub
echo    - Include the error messages shown above
echo    - Mention your Windows version
echo    - Attach a screenshot of the errors
echo.
echo 💬 Discord Support:
echo    - Join the project Discord server
echo    - Share your error logs in #support
echo.
echo 📋 System Info to Include:
%PYTHON_CMD% -c "import sys, platform; print(f'Python: {sys.version}'); print(f'OS: {platform.system()} {platform.release()}')" 2>nul || echo Could not get system info
echo.

:: Clean up temp files
if exist "test_result.tmp" del "test_result.tmp"

pause
exit /b 1

:: =============================================================================
:: END OF SCRIPT
:: =============================================================================