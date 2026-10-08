#!/usr/bin/env python3
"""Native Aural window with an isolated, embedded YouTube browser."""
import json
import re
import sys
import threading
if '--self-test' in sys.argv:
    import os, tempfile
    # Never touch a real user's library when running the packaged test mode.
    _test_directory=tempfile.mkdtemp(prefix='aural-self-test-')
    os.environ['AURAL_DATA']=_test_directory
    os.environ['XDG_DATA_HOME']=_test_directory
    os.environ['XDG_CACHE_HOME']=_test_directory
    os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    os.environ['QTWEBENGINE_CHROMIUM_FLAGS']='--disable-gpu --autoplay-policy=no-user-gesture-required'
# A frozen download worker must dispatch before importing Qt or the backend.
if len(sys.argv)>1 and sys.argv[1]=='--download-worker':
    # A Windows GUI executable has no Python stdout even when launched with PIPE.
    if sys.platform=='win32' and sys.stdout is None:
        import ctypes, msvcrt, os
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.GetStdHandle.argtypes=[ctypes.c_ulong]
        kernel.GetStdHandle.restype=ctypes.c_void_p
        handle=kernel.GetStdHandle(-11 & 0xffffffff)
        if handle not in (None,ctypes.c_void_p(-1).value):
            fd=msvcrt.open_osfhandle(handle,os.O_WRONLY)
            sys.stdout=os.fdopen(fd,'w',encoding='utf-8',errors='replace',buffering=1)
        else:sys.stdout=open(os.devnull,'w',encoding='utf-8')
        sys.stderr=sys.stdout
        sys.stdin=open(os.devnull,'r',encoding='utf-8')
    import yt_dlp
    yt_dlp.main(sys.argv[2:])
    sys.exit(0)
from urllib.parse import urlparse, parse_qs, quote
try:
    from PySide6.QtCore import QUrl, Qt, Signal, QLockFile, QTimer
    from PySide6.QtGui import QIcon, QPixmap, QPainter
    from PySide6.QtWidgets import QApplication, QMainWindow, QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QLabel
    from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineUrlRequestInterceptor, QWebEngineScript
    from PySide6.QtWebEngineWidgets import QWebEngineView
except ImportError:
    sys.exit('Install PySide6 with Qt WebEngine first. See README.md for Linux setup.')
from app import DATA, Handler, ThreadingHTTPServer, read_settings, clear_temporary
from runtime import APP_ROOT, dependency_error
from browser_support import blocked_request, DRAG_SCRIPT, COSMETIC_SCRIPT, music_theme_script
PALETTE_COLORS={'sage':'#d1f294','violet':'#c7b5ff','ocean':'#9eddea','rose':'#f3b3c4','amber':'#eac58c','mono':'#e0e0e0'}
PALETTE_SURFACES={'sage':'#26321e','violet':'#2b253d','ocean':'#1e3139','rose':'#37242c','amber':'#342d20','mono':'#292929'}
from pathlib import Path


def video_link(value):
    parsed = urlparse(value)
    if parsed.scheme != 'https' or parsed.hostname not in ('youtube.com','www.youtube.com','m.youtube.com','music.youtube.com','youtu.be'):
        return None
    parts = parsed.path.strip('/').split('/')
    video_id = parts[0] if parsed.hostname == 'youtu.be' else parse_qs(parsed.query).get('v',[''])[0]
    if not video_id and len(parts) > 1 and parts[0] in ('shorts','live','embed'):
        video_id = parts[1]
    return 'https://music.youtube.com/watch?v=' + video_id if re.fullmatch(r'[\w-]{11}',video_id, flags=re.ASCII) else None


class LibraryPage(QWebEnginePage):
    youtubeRequested = Signal()
    closeReady = Signal()
    def __init__(self, profile, parent, origin):
        super().__init__(profile, parent)
        self.origin = origin
    def acceptNavigationRequest(self, url, navigation_type, main_frame):
        if url.scheme() == 'aural' and url.host() == 'close':
            self.closeReady.emit();return False
        if url.scheme() == 'aural' and url.host() == 'youtube':
            self.youtubeRequested.emit()
            return False
        if main_frame:
            return url.toString().startswith(self.origin + '/')
        return True


class YouTubeView(QWebEngineView):
    def createWindow(self, window_type):
        # Handle links that request a new tab inside this app's existing browser.
        return self


class AdFilter(QWebEngineUrlRequestInterceptor):
    def __init__(self, parent=None):
        super().__init__(parent);self.enabled=True
    def interceptRequest(self, info):
        if self.enabled and blocked_request(info.requestUrl().toString()):info.block(True)

class LibraryView(QWebEngineView):
    linkDropped=Signal(str)
    @staticmethod
    def drop_link(mime):
        if mime.hasFormat('application/x-aural-track'):return None
        values=[url.toString() for url in mime.urls()] if mime.hasUrls() else mime.text().splitlines()
        return next((video_link(value.strip()) for value in values if video_link(value.strip())),None)
    def dragEnterEvent(self,event):
        if self.drop_link(event.mimeData()):event.acceptProposedAction()
        else:super().dragEnterEvent(event)
    def dragMoveEvent(self,event):
        if self.drop_link(event.mimeData()):event.acceptProposedAction()
        else:super().dragMoveEvent(event)
    def dropEvent(self,event):
        link=self.drop_link(event.mimeData())
        if link:event.acceptProposedAction();self.linkDropped.emit(link)
        else:super().dropEvent(event)


class Window(QMainWindow):
    def __init__(self, origin):
        super().__init__()
        self.setWindowTitle('Aural')
        self.resize(1480, 940)
        # Local library and remote website have separate storage and no shared bridge.
        self.library_profile = QWebEngineProfile('aural-library', self)
        self.library_profile.setPersistentStoragePath(str(DATA / 'library-browser'))
        self.library_profile.setCachePath(str(DATA / 'library-cache'))
        self.youtube_profile = QWebEngineProfile('aural-youtube', self)
        self.youtube_profile.setPersistentStoragePath(str(DATA / 'youtube-browser'))
        self.youtube_profile.setCachePath(str(DATA / 'youtube-cache'))
        self.library = LibraryView()
        self.library.setAcceptDrops(True)
        self.library.linkDropped.connect(lambda url: self.library.page().runJavaScript("window.auralDropLink(" + json.dumps(url) + ")"))
        self.library_page = LibraryPage(self.library_profile, self.library, origin)
        self.library.setPage(self.library_page)
        self.library_page.youtubeRequested.connect(self.open_youtube)
        self.library_page.closeReady.connect(self.finish_close)
        self.closing=False
        self.close_ready=False
        self.setCentralWidget(self.library)
        self.dock = QDockWidget('YouTube Music', self)
        self.dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
        self.dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetClosable)
        container = QWidget()
        layout = QVBoxLayout(container)
        controls = QHBoxLayout()
        self.youtube = YouTubeView()
        self.youtube.setPage(QWebEnginePage(self.youtube_profile, self.youtube))
        self.ad_filter=AdFilter(self.youtube_profile)
        self.youtube_profile.setUrlRequestInterceptor(self.ad_filter)
        drag_script=QWebEngineScript()
        drag_script.setName('aural-music-drag')
        drag_script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentReady)
        drag_script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        drag_script.setSourceCode(DRAG_SCRIPT)
        self.youtube_profile.scripts().insert(drag_script)
        self.settings_timer=QTimer(self)
        self.settings_timer.timeout.connect(self.sync_settings)
        self.settings_timer.start(1000)
        self.filter_enabled=None
        self.theme_palette=None
        for label, action in [('Back', self.youtube.back), ('Forward', self.youtube.forward), ('Reload', self.youtube.reload), ('Home', lambda: self.youtube.setUrl(QUrl('https://music.youtube.com/')))]:
            button = QPushButton(label); button.setIcon(self.browser_icon({'Back':'arrow-left','Forward':'arrow-right','Reload':'rotate-cw','Home':'home'}[label])); button.clicked.connect(action); controls.addWidget(button)
        layout.addLayout(controls)
        self.address = QLineEdit()
        self.address.setPlaceholderText('Search YouTube Music')
        self.address.returnPressed.connect(self.navigate)
        layout.addWidget(self.address)
        actions = QHBoxLayout()
        self.copy = QPushButton('Copy link')
        self.add = QPushButton('Add music')
        self.copy.setIcon(self.browser_icon('copy'))
        self.add.setIcon(self.browser_icon('download'))
        self.copy.clicked.connect(self.copy_link)
        self.add.clicked.connect(self.add_link)
        actions.addWidget(self.copy); actions.addWidget(self.add)
        layout.addLayout(actions)
        self.message = QLabel('Drag a song into your library to download it.')
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        layout.addWidget(self.youtube, 1)
        self.dock.setWidget(container)
        self.dock.setMinimumWidth(520)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock)
        self.dock.hide()
        self.youtube.urlChanged.connect(self.update_url)
        self.youtube.loadFinished.connect(self.loaded)
        self.copy.setEnabled(False); self.add.setEnabled(False)
        self.library.loadFinished.connect(lambda ok: self.library.page().runJavaScript('window.auralDesktop = true') if ok else None)
        self.library.setUrl(QUrl(origin + '/'))
        self.youtube_started = False
        self.sync_settings()
    def closeEvent(self,event):
        if self.close_ready:event.accept();return
        event.ignore()
        if self.closing:return
        self.closing=True
        self.library.page().runJavaScript("(async()=>{try{media.pause();flushListening();await listenQueue;await api('/api/session/end',{})}catch{}location.href='aural://close'})()")
        QTimer.singleShot(1500,self.finish_close)
    def finish_close(self):
        if self.close_ready:return
        self.close_ready=True;self.close()
    def browser_icon(self,name):
        from PySide6.QtSvg import QSvgRenderer
        source=(Path(__file__).parent/'static'/'icons'/(name+'.svg')).read_bytes().replace(b'currentColor',b'#bac0b7')
        renderer=QSvgRenderer(source);pixmap=QPixmap(20,20);pixmap.fill(Qt.GlobalColor.transparent)
        painter=QPainter(pixmap);renderer.render(painter);painter.end();return QIcon(pixmap)
    def open_youtube(self):
        self.dock.show()
        if not self.youtube_started:
            self.youtube.setUrl(QUrl('https://music.youtube.com/'))
            self.youtube_started = True
    def navigate(self):
        value = self.address.text().strip()
        if not value: return
        link = video_link(value)
        self.youtube.setUrl(QUrl(link) if link else QUrl('https://music.youtube.com/search?q=' + quote(value)))
    def update_url(self, url):
        self.address.setText(url.toString())
        supported = bool(video_link(url.toString()))
        self.copy.setEnabled(supported); self.add.setEnabled(supported)
        self.message.setText('Drag to your library, copy the link, or add this song.' if supported else 'Drag a song into your library to download it.')
    def apply_theme(self, palette):
        accent=PALETTE_COLORS[palette];surface=PALETTE_SURFACES[palette]
        self.setStyleSheet(f"""
            QMainWindow,QWidget{{background:#121512;color:#ebeee7;}}
            QLineEdit{{background:{surface};border:1px solid #3a4037;border-radius:7px;padding:10px;selection-background-color:{accent};selection-color:#162012;}}
            QPushButton{{background:{surface};border:0;border-radius:7px;padding:10px 14px;}}
            QPushButton:hover{{border:1px solid {accent};}}
            QPushButton:disabled{{color:#697065;}}
            QDockWidget::title{{padding:12px;background:{surface};}}
            QLabel{{color:#929b8d;}}
        """)
        from branding import write_icons, refresh_shortcuts
        png,ico=write_icons(palette,DATA)
        icon=QIcon(str(png));QApplication.setWindowIcon(icon);self.setWindowIcon(icon)
        try:refresh_shortcuts(png,ico)
        except OSError:pass
        self.add.setStyleSheet('background:'+accent+';color:#162012;font-weight:bold;')
        self.youtube.page().runJavaScript(music_theme_script(accent,surface))
    def sync_settings(self):
        try:config=read_settings();enabled=config['adblock'];palette=config['palette']
        except (OSError,ValueError):return
        self.ad_filter.enabled=enabled
        if palette!=self.theme_palette:
            self.theme_palette=palette
            self.apply_theme(palette)
        if enabled!=self.filter_enabled:
            self.filter_enabled=enabled
            self.youtube.page().runJavaScript(COSMETIC_SCRIPT.replace('ENABLED','true' if enabled else 'false'))
    def loaded(self, ok):
        if ok:
            self.youtube.page().runJavaScript(COSMETIC_SCRIPT.replace('ENABLED','true' if self.ad_filter.enabled else 'false'))
            self.apply_theme(self.theme_palette or 'sage')
        if not ok: self.message.setText('YouTube could not load. Check your connection and press reload.')
    def copy_link(self):
        link = video_link(self.youtube.url().toString())
        if link:
            QApplication.clipboard().setText(link)
            self.message.setText('Link copied.')
    def add_link(self):
        link = video_link(self.youtube.url().toString())
        if link:
            self.library.page().runJavaScript('window.auralDropLink(' + json.dumps(link) + ')')
            self.message.setText('Audio download requested.')


def main():
    import logging
    from logging.handlers import RotatingFileHandler
    handler=RotatingFileHandler(DATA/'aural.log',maxBytes=1_000_000,backupCount=2,encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logging.getLogger('aural').addHandler(handler)
    logging.getLogger('aural').setLevel(logging.INFO)
    if sys.platform=='win32':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('io.aural.Aural')
    application = QApplication(sys.argv)
    application.setApplicationName('aural')
    application.setDesktopFileName('io.aural.Aural')
    application.setWindowIcon(QIcon(str(APP_ROOT / 'static' / ('aural.ico' if sys.platform=='win32' else 'aural.png'))))
    missing=dependency_error()
    if missing:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(None,'Aural — Missing dependency',missing)
        return 1
    instance_lock=QLockFile(str(DATA / 'desktop.lock'))
    if not instance_lock.tryLock(100):
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(None,'Aural','Aural is already running. Open its existing window.')
        return 0
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    window = Window('http://127.0.0.1:' + str(server.server_port))
    window.show()
    try: return application.exec()
    finally:
        clear_temporary()
        server.shutdown()
        server.server_close()

if __name__ == '__main__':
    if '--self-test' in sys.argv:
        from smoke_test import run
        sys.exit(run())
    sys.exit(main())
