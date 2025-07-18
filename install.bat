@echo off
color 0A
cls

echo ========================================
echo      Voice Connector - Installer
echo ========================================
echo.

echo [*] Checking Python installation...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.7 or later from:
    echo https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation
    timeout /t 5 >nul
    exit /b 1
)

echo [OK] Python is installed

echo.
echo [*] Installing required Python packages...
python -m pip install --upgrade pip
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to upgrade pip
    timeout /t 5 >nul
    exit /b 1
)

pip install websockets python-dotenv colorama pyfiglet ascii-magic
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install required packages
    timeout /t 5 >nul
    exit /b 1
)

echo [OK] All packages installed successfully

echo.
echo [*] Checking for .env file...
if not exist ".\.env" (
    echo [*] Creating .env file...
    (
        echo # Discord Bot Token - Get it from https://discord.com/developers/applications
        echo TOKEN=
        echo.
        echo # Discord Status (online/dnd/idle)
        echo DISCORD_STATUS=dnd
        echo.
        echo # Server ID (Right-click on server icon -> Copy Server ID)
        echo GUILD_ID=1369593883993837578
        echo.
        echo # Voice Channel ID (Right-click on voice channel -> Copy Channel ID)
        echo CHANNEL_ID=1395728315494436904
        echo.
        echo # Self Mute in Voice (True/False)
        echo SELF_MUTE=True
        echo.
        echo # Self Deafen in Voice (True/False)
        echo SELF_DEAF=False
    ) > .env
    
    echo [OK] .env file created
    call :CheckToken
) else (
    echo [OK] .env file already exists
    call :CheckToken
)

goto :eof

:CheckToken
findstr /i /c:"TOKEN=" .env | findstr /i /c:"TOKEN=$" >nul
if %ERRORLEVEL% EQU 0 (
    echo [WARNING] No Discord token found in .env file
    echo [*] Opening .env file for editing...
    start notepad .env
    
    powershell -command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show('Please add your Discord token to the .env file and save it. Then run the installer again.', 'Token Required', [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Warning)"
    
    echo [*] Please add your Discord token to the .env file and run this script again.
    pause
    exit /b 1
) else (
    echo [OK] Discord token found in .env file
    echo [*] Starting Voice Connector...
    python voice_connector.py
    pause
)

goto :eof
