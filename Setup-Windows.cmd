@echo off
setlocal
cd /d "%~dp0"
py -3.12 -m venv .venv-win
if errorlevel 1 goto fail
.venv-win\Scripts\python.exe -m pip install -r requirements-windows.txt
if errorlevel 1 goto fail
.venv-win\Scripts\python.exe packaging\windows\prepare_tools.py
if errorlevel 1 goto fail
.venv-win\Scripts\python.exe install.py
if errorlevel 1 goto fail
echo Installed. Search for Aural in the Start menu.
pause
exit /b 0
:fail
echo Setup failed. Check the error above. Python 3.12 x64 and internet access are required.
pause
exit /b 1
