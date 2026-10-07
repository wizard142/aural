"""Platform paths and subprocess setup shared by source and packaged builds."""
import os
from pathlib import Path
import shutil
import subprocess
import sys

APP_ROOT = Path(__file__).resolve().parent

def data_directory(platform=None, env=None, home=None):
    platform = platform or sys.platform
    env = os.environ if env is None else env
    home = Path.home() if home is None else Path(home)
    override = env.get('AURAL_DATA')
    if override:
        return Path(override).expanduser()
    if platform == 'win32':
        return Path(env.get('LOCALAPPDATA', str(home / 'AppData' / 'Local'))) / 'Aural'
    if platform == 'darwin':
        return home / 'Library' / 'Application Support' / 'Aural'
    return Path(env.get('XDG_DATA_HOME', str(home / '.local' / 'share'))) / 'aural'

def binary(name):
    filename = name + ('.exe' if sys.platform == 'win32' else '')
    override = os.environ.get('AURAL_' + name.upper().replace('-', '_'))
    if override:
        path = Path(override).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f'{name} was not found at {path}')
        return str(path.resolve())
    bundled = APP_ROOT / 'vendor' / 'bin' / filename
    if bundled.is_file():
        return str(bundled)
    found = shutil.which(filename)
    if not found:
        raise FileNotFoundError(f'{name} is missing. Install it or use the complete Aural Windows package.')
    return found

def downloader_command():
    # Packaged Windows workers run the same executable without starting Qt.
    if getattr(sys, 'frozen', False):
        return [sys.executable, '--download-worker']
    if sys.platform == 'win32':
        return [sys.executable, '-m', 'yt_dlp']
    return [binary('yt-dlp')]

def child_environment():
    env = os.environ.copy()
    env['PATH'] = str(APP_ROOT / 'vendor' / 'bin') + os.pathsep + env.get('PATH', '')
    # Qt/PyInstaller's DLL search directories should not affect external tools.
    if sys.platform != 'win32' and 'LD_LIBRARY_PATH_ORIG' in env:
        env['LD_LIBRARY_PATH'] = env['LD_LIBRARY_PATH_ORIG']
    return env

def subprocess_options():
    result = dict(stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                  stderr=subprocess.STDOUT, text=True, encoding='utf-8',
                  errors='replace', env=child_environment())
    if sys.platform == 'win32':
        result['creationflags'] = subprocess.CREATE_NO_WINDOW
    return result

def dependency_error():
    try:
        binary('ffmpeg'); binary('ffprobe')
        if not getattr(sys, 'frozen', False):
            if sys.platform == 'win32':
                import importlib.util
                if importlib.util.find_spec('yt_dlp') is None:
                    return 'yt-dlp is missing. Install requirements-windows.txt.'
            else:
                binary('yt-dlp')
    except FileNotFoundError as error:
        return str(error)
    return None
