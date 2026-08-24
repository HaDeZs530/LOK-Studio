@echo off
setlocal
rem ============================================================
rem  LOK STUDIO — double-click to launch.
rem  First run installs pywebview (one-time, ~10 seconds).
rem ============================================================
cd /d "%~dp0"
set "PY=python"
where python >nul 2>nul || set "PY=py"
%PY% -c "import webview" 2>nul || (
  echo First run: installing pywebview...
  %PY% -m pip install --quiet pywebview
)
%PY% app\main.py %*
if errorlevel 1 pause
