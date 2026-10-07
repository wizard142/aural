@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv-win\Scripts\pythonw.exe" (
  echo Run Setup-Windows.cmd first.
  pause
  exit /b 1
)
start "Aural" ".venv-win\Scripts\pythonw.exe" "desktop.py"
