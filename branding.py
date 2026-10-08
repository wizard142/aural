"""Theme-colored brand assets for the UI, window and installed shortcuts."""
import os
from pathlib import Path
import sys
from runtime import APP_ROOT, data_directory

COLORS={'sage':'#d1f294','violet':'#c7b5ff','ocean':'#9eddea','rose':'#f3b3c4','amber':'#eac58c','mono':'#e0e0e0'}
SURFACES={'sage':'#26321e','violet':'#2b253d','ocean':'#1e3139','rose':'#37242c','amber':'#342d20','mono':'#292929'}

def logo_svg(palette):
    from PySide6.QtGui import QColor
    color=QColor(COLORS[palette])
    source=(APP_ROOT/'static'/'aural.svg').read_text(encoding='utf-8')
    return source.replace('#e1ffb3',color.lighter(110).name()).replace('#9fca6d',color.darker(110).name()).replace('#172013','#121512').replace('#34482a',SURFACES[palette])

def write_icons(palette,data=None):
    from PySide6.QtGui import QImage,QPainter
    from PySide6.QtSvg import QSvgRenderer
    from PIL import Image
    directory=Path(data or data_directory())/'icons';directory.mkdir(parents=True,exist_ok=True)
    png=directory/'aural.png';ico=directory/'aural.ico'
    image=QImage(256,256,QImage.Format.Format_ARGB32);image.fill(0)
    painter=QPainter(image);QSvgRenderer(logo_svg(palette).encode()).render(painter);painter.end()
    scratch=directory/'aural-new.png'
    if not image.save(str(scratch),'PNG'):raise OSError('Could not write theme icon')
    scratch.replace(png)
    with Image.open(png) as bitmap:
        temp=directory/'aural-new.ico';bitmap.save(temp,format='ICO',sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
        temp.replace(ico)
    return png,ico

def refresh_shortcuts(png,ico):
    if sys.platform=='win32':
        import ctypes
        # Installed and source shortcuts reference this persistent user icon.
        ctypes.windll.shell32.SHChangeNotify(0x08000000,0,None,None)
    elif sys.platform.startswith('linux'):
        file=Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))/'applications'/'io.aural.Aural.desktop'
        if file.is_file():
            content=file.read_text(encoding='utf-8')
            changed='\n'.join('Icon='+str(png) if line.startswith('Icon=') else line for line in content.split('\n'))
            if changed!=content:file.write_text(changed,encoding='utf-8')
            else:file.touch()
