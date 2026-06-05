@echo off
setlocal
cd /d "%~dp0"
set "ROOT=%~dp0"

echo ============================================
echo  Sonobuoy Acoustic Analysis System
echo ============================================
echo.

:: ── Check prerequisites ──
where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: python is not installed or not in PATH.
    pause
    exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
    where npm.cmd >nul 2>&1
    if errorlevel 1 (
        echo Node.js is not installed. Installing now...
        echo.

        :: Download Node.js LTS installer using PowerShell
        set "NODE_INSTALLER=%TEMP%\node-install.msi"
        echo Downloading Node.js LTS installer...
        powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://nodejs.org/dist/v22.16.0/node-v22.16.0-x64.msi' -OutFile '%TEMP%\node-install.msi'"
        if errorlevel 1 (
            echo ERROR: Failed to download Node.js installer.
            echo Please install manually from https://nodejs.org/
            pause
            exit /b 1
        )

        echo Installing Node.js (this may ask for admin permission)...
        msiexec /i "%TEMP%\node-install.msi" /qb
        if errorlevel 1 (
            echo ERROR: Node.js installation failed.
            echo Please install manually from https://nodejs.org/
            pause
            exit /b 1
        )

        del "%TEMP%\node-install.msi" >nul 2>&1

        :: Refresh PATH so npm is available in this session
        set "PATH=%ProgramFiles%\nodejs;%PATH%"

        where npm >nul 2>&1
        if errorlevel 1 (
            where npm.cmd >nul 2>&1
            if errorlevel 1 (
                echo ERROR: Node.js installed but npm still not found.
                echo Please close this window, open a new terminal, and run run.bat again.
                pause
                exit /b 1
            )
        )
        echo Node.js installed successfully.
        echo.
    )
)

:: ── Install backend dependencies ──
echo [1/3] Installing backend dependencies...
cd /d "%ROOT%backend"
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo ERROR: Failed to install backend dependencies.
    pause
    exit /b 1
)
cd /d "%ROOT%"

:: ── Install frontend dependencies ──
echo [2/3] Installing frontend dependencies...
cd /d "%ROOT%frontend"
call npm install --legacy-peer-deps
if errorlevel 1 (
    echo ERROR: Failed to install frontend dependencies.
    pause
    exit /b 1
)
echo      Frontend dependencies installed successfully.
cd /d "%ROOT%"

:: ── Start backend server ──
echo [3/3] Starting servers...
echo.
echo  Backend  : http://localhost:8000
echo  Frontend : http://localhost:3000
echo.
echo  Close this window to stop the frontend.
echo  Close the minimized "Sonobuoy Backend" window to stop the backend.
echo ============================================

start "Sonobuoy Backend" /min cmd /c "cd /d "%ROOT%backend" && python server.py"

:: Give backend a moment to start
timeout /t 4 /nobreak >nul

:: ── Start frontend dev server ──
echo.
echo Starting frontend...
cd /d "%ROOT%frontend"
set REACT_APP_API_URL=http://localhost:8000/api
call npm start

:: If we get here, frontend exited
echo.
echo Frontend stopped.
pause