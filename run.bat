@echo off
cd /d "%~dp0"

echo ============================================
echo  Sonobuoy Acoustic Analysis System
echo ============================================
echo.

:: ── Install backend dependencies ──
echo [1/3] Installing backend dependencies...
cd backend
pip install -r requirements.txt --quiet
cd ..

:: ── Install frontend dependencies ──
echo [2/3] Installing frontend dependencies...
cd frontend
call npm install --legacy-peer-deps --silent
cd ..

:: ── Start backend server ──
echo [3/3] Starting servers...
echo.
echo  Backend  : http://localhost:8000
echo  Frontend : http://localhost:3000
echo.
echo  Press Ctrl+C in this window to stop both servers.
echo ============================================

start "Sonobuoy Backend" /min cmd /c "cd /d "%~dp0backend" && python server.py"

:: Give backend a moment to start
timeout /t 3 /nobreak >nul

:: ── Start frontend dev server ──
cd frontend
set REACT_APP_API_URL=http://localhost:8000/api
call npm start