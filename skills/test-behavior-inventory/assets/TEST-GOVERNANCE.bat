@echo off
rem TEST-GOVERNANCE launcher: serve this directory over HTTP and open the viewer.
rem The viewer reads BEHAVIORS.md / TEST-DISPOSITION.md live; browsers block file://
rem fetches, so the local server is required.
rem If port 8765 is already in use (usually our own running instance), the newly
rem started server exits quietly and the browser still reaches the running one.
cd /d "%~dp0"
where python >nul 2>nul && set "PY=python"
if not defined PY where py >nul 2>nul && set "PY=py"
if not defined PY (
  echo Python not found. Install Python first, then run this file again.
  pause
  exit /b 1
)
start "TEST-GOVERNANCE" /min %PY% -m http.server 8765 --bind 127.0.0.1
ping -n 2 127.0.0.1 >nul
start "" "http://127.0.0.1:8765/TEST-GOVERNANCE.html"
