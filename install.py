#!/usr/bin/env python3
"""Register a source checkout in Linux applications or the Windows Start menu."""
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
from branding import write_icons
from runtime import data_directory
import json
def install_icons():
    data=data_directory();palette='sage'
    if (data/'settings.json').exists():palette=json.loads((data/'settings.json').read_text()).get('palette','sage')
    return write_icons(palette,data)

def desktop_escape(value):
    return str(value).replace('\\','\\\\').replace('"','\\"').replace('`','\\`').replace('$','\\$').replace('%','%%')

def install_windows():
    python=ROOT/'.venv-win'/'Scripts'/'python.exe'
    pythonw=python.with_name('pythonw.exe')
    if not python.is_file() or not pythonw.is_file():raise RuntimeError('Run Setup-Windows.cmd first.')
    subprocess.run([str(python),'-c','from PySide6.QtWebEngineWidgets import QWebEngineView'],check=True)
    roaming=Path(os.environ.get('APPDATA',str(Path.home()/'AppData'/'Roaming')))
    programs=roaming/'Microsoft'/'Windows'/'Start Menu'/'Programs'
    programs.mkdir(parents=True,exist_ok=True)
    env=os.environ.copy()
    env.update(AURAL_SHORTCUT_FILE=str(programs/'Aural.lnk'),AURAL_SHORTCUT_TARGET=str(pythonw),AURAL_SHORTCUT_ROOT=str(ROOT),AURAL_SHORTCUT_ICON=str(install_icons()[1]))
    # Paths are passed in environment variables, not interpolated into shell code.
    script=r'''
$ErrorActionPreference='Stop'
$shell=New-Object -ComObject WScript.Shell
$link=$shell.CreateShortcut($env:AURAL_SHORTCUT_FILE)
$link.TargetPath=$env:AURAL_SHORTCUT_TARGET
$link.Arguments='"'+(Join-Path $env:AURAL_SHORTCUT_ROOT 'desktop.py')+'"'
$link.WorkingDirectory=$env:AURAL_SHORTCUT_ROOT
$link.IconLocation=$env:AURAL_SHORTCUT_ICON+',0'
$link.Description='Aural music library'
$link.Save()
'''
    subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],env=env,check=True)
    print('Installed Start-menu shortcut:',programs/'Aural.lnk')

def install_linux():
    python=ROOT/'.venv'/'bin'/'python'
    if not python.exists():raise RuntimeError('Create .venv and install requirements.txt first.')
    subprocess.run([str(python),'-c','from PySide6.QtWebEngineWidgets import QWebEngineView'],check=True)
    base=Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))
    applications=base/'applications';applications.mkdir(parents=True,exist_ok=True)
    entry=f'''[Desktop Entry]
Type=Application
Version=1.0
Name=Aural
GenericName=Music Library
Comment=Music and playlists stored locally
Exec="{desktop_escape(python)}" "{desktop_escape(ROOT/'desktop.py')}"
Path={ROOT}
Icon={install_icons()[0]}
Terminal=false
Categories=AudioVideo;Audio;Player;
Keywords=Music;YouTube;Playlist;Offline;
StartupWMClass=aural
'''
    target=applications/'io.aural.Aural.desktop';target.write_text(entry)
    if shutil.which('update-desktop-database'):subprocess.run(['update-desktop-database',str(applications)],check=False)
    print('Installed launcher:',target)

def main():
    try:
        if sys.platform=='win32':install_windows()
        else:install_linux()
    except (RuntimeError,OSError,subprocess.CalledProcessError) as error:
        sys.exit(str(error))
    print('Search for Aural in your application menu. Keep this app directory in place.')

if __name__=='__main__':main()
