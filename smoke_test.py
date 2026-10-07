"""Isolated desktop and download smoke test, usable in a frozen Windows build."""
import functools
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import wave
from http.server import SimpleHTTPRequestHandler


def run():
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer, QMimeData, QUrl, QPoint, QPointF, Qt
    from PySide6.QtGui import QDragEnterEvent, QDropEvent
    from app import DATA, Handler, ThreadingHTTPServer, insights
    from desktop import Window
    from runtime import APP_ROOT, binary, subprocess_options, dependency_error
    from browser_support import blocked_request

    output = Path(sys.argv[sys.argv.index('--self-test-result')+1]).resolve() if '--self-test-result' in sys.argv else DATA/'smoke-result.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    results = {'platform': sys.platform, 'frozen': bool(getattr(sys, 'frozen', False)), 'checks': {}, 'errors': []}
    application = QApplication(sys.argv)
    application.setApplicationName('aural-self-test')
    server = None
    fixture_server = None
    window = None
    exit_code = [1]
    started = time.monotonic()

    def save():
        results['elapsed_seconds'] = round(time.monotonic()-started, 2)
        output.write_text(json.dumps(results, indent=2), encoding='utf-8')

    try:
        missing = dependency_error()
        if missing: raise RuntimeError(missing)
        # A locally generated fixture avoids downloads of anyone else's content.
        fixtures = DATA/'fixtures'
        fixtures.mkdir(exist_ok=True)
        wav = fixtures/'fixture.wav'
        with wave.open(str(wav), 'wb') as file:
            file.setnchannels(1); file.setsampwidth(2); file.setframerate(16000)
            file.writeframes(b'\x00\x00' * 16000 * 12)
        stem = 'dQw4w9WgXcQ-audio'
        options = subprocess_options()
        converted = subprocess.run([binary('ffmpeg'),'-hide_banner','-loglevel','error','-y','-i',str(wav),str(DATA/(stem+'.mp3'))], timeout=45, **options)
        if converted.returncode: raise RuntimeError('FFmpeg fixture conversion failed: '+converted.stdout)
        (DATA/(stem+'.info.json')).write_text(json.dumps({'title':'Playback fixture','uploader':'Aural tests','duration':12}), encoding='utf-8')
        results['checks']['ffmpeg_conversion'] = True
        class FixtureHandler(SimpleHTTPRequestHandler):
            def log_message(self, *args): pass
        fixture_server = ThreadingHTTPServer(('127.0.0.1',0), functools.partial(FixtureHandler,directory=str(fixtures)))
        threading.Thread(target=fixture_server.serve_forever,daemon=True).start()
        worker = [sys.executable,'--download-worker'] if getattr(sys,'frozen',False) else [sys.executable,str(APP_ROOT/'desktop.py'),'--download-worker']
        converted = subprocess.run(worker+['--ignore-config','--no-playlist','--newline','-x','--audio-format','mp3','--ffmpeg-location',str(Path(binary('ffmpeg')).parent),'-o',str(fixtures/'downloaded.%(ext)s'),'--',f'http://127.0.0.1:{fixture_server.server_port}/fixture.wav'],timeout=90,**options)
        if converted.returncode or not (fixtures/'downloaded.mp3').is_file():
            raise RuntimeError('Download worker/conversion failed: '+converted.stdout[-3000:])
        results['checks']['download_worker_and_conversion'] = True
        server = ThreadingHTTPServer(('127.0.0.1',0), Handler)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        window = Window(f'http://127.0.0.1:{server.server_port}')
        window.show()
        results['checks']['request_filter'] = blocked_request('https://ads.doubleclick.net/ad') and not blocked_request('https://music.youtube.com/watch?v=dQw4w9WgXcQ')
        script = r'''
        (async()=>{const checks={};try{
          await refresh();
          if(!tracks.length)throw Error('Fixture did not load');
          media.muted=true;playTrack(tracks[0]);
          await new Promise(r=>setTimeout(r,600));
          if(media.paused||media.error)throw Error('MP3 did not play');checks.playback=true;
          await $('#favorite').onclick();
          if(!$('#favorite').classList.contains('liked')||$('#favorite').getAttribute('aria-pressed')!=='true')throw Error('Favorite did not light up');
          if(!$('#favorite .icon').style.maskImage.includes('heart-filled.svg'))throw Error('Filled heart missing');
          const likedColor=getComputedStyle($('#favorite')).color;
          if(likedColor!==getComputedStyle($('.play')).backgroundColor)throw Error('Favorite color does not follow theme');
          await refresh();if(!favorites.has(tracks[0].id))throw Error('Favorite did not persist');checks.favorite_on=true;
          await $('#favorite').onclick();await refresh();
          if(favorites.has(tracks[0].id)||$('#favorite').classList.contains('liked')||$('#favorite').getAttribute('aria-pressed')!=='false')throw Error('Unlike failed');checks.favorite_off=true;
          await api('/api/playlists',{name:'Test playlist',color:'#9eddea'});await refresh();
          const data=new DataTransfer();data.setData('application/x-aural-track',tracks[0].id);
          document.querySelector('.playlist-nav').dispatchEvent(new DragEvent('drop',{dataTransfer:data,bubbles:true,cancelable:true}));
          await new Promise(r=>setTimeout(r,600));await refresh();
          if(!playlistData[0].tracks.includes(tracks[0].id))throw Error('Playlist drop failed');checks.playlist_drag=true;
          if(!document.querySelector('.track-card.in-playlist')||document.querySelector('.track-card').style.getPropertyValue('--playlist-outline')!=='#9eddea')throw Error('Playlist outline missing');checks.playlist_outline=true;
          for(const palette of Object.keys(palettes)){
            settings=await api('/api/settings',{palette});theme();
            if(getComputedStyle(document.documentElement).getPropertyValue('--green').trim()!==palettes[palette][0])throw Error('Palette failed: '+palette);
          }checks.palettes=true;
          for(const layout of ['grid','list','compact']){settings=await api('/api/settings',{layout});theme();if(document.body.dataset.layout!==layout)throw Error('Layout failed: '+layout)}checks.layouts=true;
          $('#settings-open').click();if(!$('#settings-modal').open)throw Error('Settings drawer failed');$('#settings-close').click();checks.settings_drawer=true;
          try{await api('/api/download',{url:'https://music.youtube.com/watch?v=dQw4w9WgXcQ',kind:'audio'});throw Error('Duplicate accepted')}catch(e){if(!e.message.includes('already in your library'))throw e}checks.duplicates=true;
          try{await api('/api/download',{url:'https://music.youtube.com/watch?v=dQw4w9WgXcQ',kind:'video'});throw Error('Video accepted')}catch(e){if(!e.message.includes('audio downloads only'))throw e}checks.audio_only=true;
          await new Promise(r=>setTimeout(r,7300));media.pause();flushListening();await listenQueue;
          const stats=await(await fetch('/api/insights')).json();if(stats.seconds<6||stats.plays<1)throw Error('Listening not counted');checks.listening_history=true;
          $('#favorite').click();await new Promise(r=>setTimeout(r,200));await refresh();
          showTrackOptions(tracks[0]);const oldConfirm=window.confirm;window.confirm=()=>true;await $('#remove-track').onclick();window.confirm=oldConfirm;
          if(tracks.length||playlistData[0].tracks.length)throw Error('Delete cleanup failed');checks.deletion=true;
          window.smokeStatus={done:true,checks};
        }catch(e){window.smokeStatus={done:true,checks,error:e.message}}
        })();
        '''
        began = [False]
        def start(ok):
            if ok and not began[0]:
                began[0] = True
                window.library.page().runJavaScript(script)
        window.library.loadFinished.connect(start)
        # loadFinished may have fired during synchronous worker setup on slow hosts.
        QTimer.singleShot(2000,lambda:start(True) if not began[0] else None)
        done = [False]
        def finish(status):
            if done[0]: return
            done[0] = True
            results['checks'].update(status.get('checks',{}))
            if status.get('error'): results['errors'].append(status['error'])
            if not results['errors']:
                mime = QMimeData();mime.setUrls([QUrl('https://music.youtube.com/watch?v=dQw4w9WgXcQ')])
                # Test drop routing without triggering an external download after fixture deletion.
                received=[]
                window.library.linkDropped.disconnect()
                window.library.linkDropped.connect(received.append)
                enter=QDragEnterEvent(QPoint(400,400),Qt.DropAction.CopyAction,mime,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier)
                QApplication.sendEvent(window.library,enter)
                drop=QDropEvent(QPointF(400,400),Qt.DropAction.CopyAction,mime,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier)
                QApplication.sendEvent(window.library,drop)
                results['checks']['native_drop']=enter.isAccepted() and drop.isAccepted() and received==['https://music.youtube.com/watch?v=dQw4w9WgXcQ']
                if not results['checks']['native_drop']:results['errors'].append('Native drag route failed')
            results['checks']['webengine_assets']=True
            window.grab().save(str(output.with_suffix('.png')))
            exit_code[0] = 0 if not results['errors'] and all(results['checks'].values()) else 1
            save();application.quit()
        def got(raw):
            if raw:
                status=json.loads(raw)
                if status.get('done'):finish(status)
        poll=QTimer();poll.timeout.connect(lambda:window.library.page().runJavaScript('JSON.stringify(window.smokeStatus||null)',got));poll.start(500)
        QTimer.singleShot(60000,lambda:finish({'error':'Desktop smoke test timed out'}))
        application.exec()
    except Exception as error:
        results['errors'].append(str(error));save()
    finally:
        for local_server in (server,fixture_server):
            if local_server:local_server.shutdown();local_server.server_close()
        if window:
            from shiboken6 import delete
            delete(window.library);delete(window.youtube);delete(window)
    return exit_code[0]
