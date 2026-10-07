# Build on Windows with: python -m PyInstaller packaging/windows/Aural.spec
from pathlib import Path
from PyInstaller.utils.hooks import collect_all
ROOT=Path(SPECPATH).resolve().parents[1]
for tool in ('ffmpeg.exe','ffprobe.exe','deno.exe'):
    if not (ROOT/'vendor'/'bin'/tool).is_file():
        raise SystemExit('Run packaging/windows/prepare_tools.py first. Missing '+tool)
datas=[(str(ROOT/'static'),'static'),(str(ROOT/'vendor'/'notices'),'vendor/notices'),(str(ROOT/'packaging'/'windows'/'WINDOWS.md'),'.')]
binaries=[(str(ROOT/'vendor'/'bin'/tool),'vendor/bin') for tool in ('ffmpeg.exe','ffprobe.exe','deno.exe')]
hiddenimports=[]
for package in ('yt_dlp','yt_dlp_ejs'):
    package_data,package_bins,package_imports=collect_all(package)
    datas+=package_data;binaries+=package_bins;hiddenimports+=package_imports
a=Analysis([str(ROOT/'desktop.py')],pathex=[str(ROOT)],binaries=binaries,datas=datas,hiddenimports=hiddenimports)
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='Aural',debug=False,bootloader_ignore_signals=False,strip=False,upx=False,console=False,icon=str(ROOT/'static'/'aural.ico'))
coll=COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='Aural')
