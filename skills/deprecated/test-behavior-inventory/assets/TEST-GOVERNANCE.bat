@echo off
rem TEST-GOVERNANCE launcher: serve this directory over HTTP and open the viewer.
rem The viewer reads BEHAVIORS.md / TEST-DISPOSITION.md live; browsers block file://
rem fetches, so the local server is required. TEST-GOVERNANCE-server.py also serves
rem /__commit, which the viewer uses to read commit times and messages from this
rem repository's git by the short hashes recorded in the two documents.
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
start "TEST-GOVERNANCE" /min %PY% "TEST-GOVERNANCE-server.py" --no-open --exit-busy
ping -n 2 127.0.0.1 >nul
start "" "http://127.0.0.1:8765/TEST-GOVERNANCE.html"
