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
    Window = sys.modules['__main__'].Window
    from runtime import APP_ROOT, binary, subprocess_options, dependency_error
    from browser_support import blocked_request

    output = Path(sys.argv[sys.argv.index('--self-test-result')+1]).resolve() if '--self-test-result' in sys.argv else DATA/'smoke-result.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    import ai_playlists
    original_provider=ai_playlists.call_provider
    original_backend=ai_playlists.secure_backend
    ai_playlists.secure_backend=lambda:None
    ai_playlists.call_provider=lambda config,prompt:{'name':'Fixture mix','reason':'Mock provider: jazz tags','track_ids':['dQw4w9WgXcQ-audio'],'annotations':[{'id':'dQw4w9WgXcQ-audio','genres':['jazz'],'confidence':.7,'evidence':'Fixture tags'}]}
    results = {'platform': sys.platform, 'frozen': bool(getattr(sys, 'frozen', False)), 'checks': {}, 'errors': []}
    if sys.platform=='win32':
        import uuid
        backend=original_backend()
        if backend is None:raise RuntimeError('Windows credential-store backend is unavailable')
        ident='self-test-'+uuid.uuid4().hex
        try:
            backend.set_password('Aural self-test',ident,'fixture-key-no-billing')
            results['checks']['windows_secure_key_store']=backend.get_password('Aural self-test',ident)=='fixture-key-no-billing'
        finally:backend.delete_password('Aural self-test',ident)
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
        (DATA/(stem+'.info.json')).write_text(json.dumps({'title':'Playback fixture','uploader':'Aural tests','duration':12,'tags':['jazz']}), encoding='utf-8')
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

          await loadAiSettings();$('#ai-provider').value='openai';$('#ai-model').value='test-model';$('#ai-key').value='test-key';$('#ai-remember').checked=false;
          await $('#ai-settings-form').onsubmit({preventDefault(){},submitter:$('#ai-settings-form button[type=submit]')});
          if(!aiConfig.has_key||$('#ai-key').value)throw Error('AI key settings failed');checks.ai_key_settings=true;
          await $('#ai-open').onclick();$('#ai-prompt').value='Calm jazz then heavier songs';$('#ai-consent').checked=true;
          await $('#ai-form').onsubmit({preventDefault(){}});
          let mix=playlistData.find(p=>p.id===activePlaylist);if(!mix?.temporary||$('#save-mix').hidden)throw Error('Temporary AI mix failed');checks.ai_temporary_mix=true;
          playlistDialog(mix);$('#playlist-name').value='Saved jazz';
          await $('#playlist-form').onsubmit({preventDefault(){},submitter:$('#playlist-form button[type=submit]')});
          mix=playlistData.find(p=>p.id===activePlaylist);if(mix.name!=='Saved jazz'||!mix.temporary)throw Error('Temporary rename failed');checks.ai_rename=true;
          await $('#save-mix').onclick();if(playlistData.find(p=>p.id===activePlaylist).temporary)throw Error('Saving AI mix failed');checks.ai_save=true;
          const profile=await(await fetch('/api/song/'+tracks[0].id)).json();if(!profile.facts.tags.includes('jazz')||profile.ai_estimate?.genres[0]!=='jazz'||profile.audio_analyzed)throw Error('Song metadata provenance failed');checks.song_metadata=true;
          const second=await api('/api/ai/generate',{prompt:'Another mix',consent:true,color:'#9eddea'});
          let completed=false;for(let i=0;i<20;i++){const jobs=await(await fetch('/api/ai/jobs')).json();if(jobs.find(j=>j.id===second.id)?.status==='complete'){completed=true;break}await new Promise(r=>setTimeout(r,100))}if(!completed)throw Error('Second mix failed');
          await api('/api/session/end',{});await refresh();if(playlistData.some(p=>p.temporary)||!playlistData.some(p=>p.name==='Saved jazz'))throw Error('Session cleanup removed a saved mix or kept a temporary mix');checks.ai_close_cleanup=true;
          const logo=await(await fetch('/api/logo.svg')).text();if(!logo.includes('#292929'))throw Error('Theme logo failed');checks.theme_logo=true;
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
        def ready(value):
            if value and not began[0]:
                began[0] = True
                window.library.page().runJavaScript(script)
        def start(ok=True):
            if ok and not began[0]:
                window.library.page().runJavaScript("typeof refresh==='function'",ready)
        window.library.loadFinished.connect(start)
        startup=QTimer();startup.timeout.connect(start);startup.start(500)
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
            from PIL import Image
            with Image.open(DATA/'icons'/'aural.png') as bitmap:
                rgb=bitmap.convert('RGB').getpixel((128,128))
                results['checks']['native_theme_icon']=max(rgb)-min(rgb)<=2
            results['checks']['webengine_assets']=True
            window.grab().save(str(output.with_suffix('.png')))
            exit_code[0] = 0 if not results['errors'] and all(results['checks'].values()) else 1
            save();application.quit()
        def got(raw):
            if raw:
                status=json.loads(raw)
                if isinstance(status,dict) and status.get('done'):finish(status)
        poll=QTimer();poll.timeout.connect(lambda:window.library.page().runJavaScript('JSON.stringify(window.smokeStatus||null)',got));poll.start(500)
        QTimer.singleShot(60000,lambda:finish({'error':'Desktop smoke test timed out'}))
        application.exec()
    except Exception as error:
        results['errors'].append(str(error));save()
    finally:
        ai_playlists.call_provider=original_provider
        ai_playlists.secure_backend=original_backend
        for local_server in (server,fixture_server):
            if local_server:local_server.shutdown();local_server.server_close()
        if window:
            from shiboken6 import delete
            delete(window.library);delete(window.youtube);delete(window)
    return exit_code[0]
