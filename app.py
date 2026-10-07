#!/usr/bin/env python3
import json, os, pathlib, re, subprocess, threading, uuid, mimetypes, sqlite3, datetime, math
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, unquote, parse_qs
from runtime import APP_ROOT, data_directory, downloader_command, binary, subprocess_options
ROOT = APP_ROOT
DATA = data_directory()
DATA.mkdir(parents=True, exist_ok=True)
lock = threading.RLock()
jobs = {}
def library():
    result = []
    for p in DATA.glob('*.info.json'):
        try:
            info = json.loads(p.read_text())
            stem = p.name[:-10]
            media = next((f for f in DATA.glob(stem + '.*') if f.suffix in ('.mp3','.m4a','.opus','.webm','.mp4','.mkv')), None)
            if media and media.suffix in ('.mp3','.m4a','.opus'):
                result.append(dict(id=stem, title=info.get('title',stem), artist=info.get('uploader','Unknown artist'), duration=info.get('duration',0), thumbnail=info.get('thumbnail',''), file=media.name, kind='audio' if media.suffix in ('.mp3','.m4a','.opus') else 'video'))
        except (ValueError, OSError): pass
    return result

def video_id(url):
    parsed=urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname not in ('youtube.com','www.youtube.com','m.youtube.com','youtu.be','music.youtube.com'): raise ValueError('Enter a valid HTTPS YouTube video link')
    parts=parsed.path.strip('/').split('/')
    value=parts[0] if parsed.hostname=='youtu.be' else parse_qs(parsed.query).get('v',[''])[0]
    if not value and len(parts)>1 and parts[0] in ('shorts','live','embed'): value=parts[1]
    if not re.fullmatch(r'[A-Za-z0-9_-]{11}',value): raise ValueError('Use a specific video link')
    return value

PLAYLISTS=DATA/'playlists.json'
def playlists():
    return json.loads(PLAYLISTS.read_text()) if PLAYLISTS.exists() else []
def save_playlists(items):
    temp=PLAYLISTS.with_suffix('.tmp');temp.write_text(json.dumps(items));temp.replace(PLAYLISTS)
def edit_playlist(body):
    items=playlists(); action=body.get('action','create'); pid=body.get('id')
    if action=='create':
        name=body.get('name','').strip();color=body.get('color','#d1f294')
        if not name or len(name)>60: raise ValueError('Playlist name must be 1–60 characters')
        if not re.fullmatch(r'#[0-9a-fA-F]{6}',color): raise ValueError('Choose a valid color')
        items.append(dict(id=uuid.uuid4().hex,name=name,color=color,tracks=[]))
    else:
        item=next((p for p in items if p['id']==pid),None)
        if not item: raise ValueError('Playlist not found')
        if action=='delete': items.remove(item)
        elif action=='update':
            name=body.get('name','').strip();color=body.get('color','')
            if not name or len(name)>60 or not re.fullmatch(r'#[0-9a-fA-F]{6}',color): raise ValueError('Choose a name and color')
            item.update(name=name,color=color)
        elif action in ('add','remove'):
            track=body.get('track')
            if action=='add':
                if track not in {t['id'] for t in library()}: raise ValueError('Track not found')
                if track not in item['tracks']: item['tracks'].append(track)
            else: item['tracks']=[t for t in item['tracks'] if t!=track]
        else: raise ValueError('Unknown playlist action')
    save_playlists(items);return items

def delete_track(track_id):
    if not isinstance(track_id,str) or track_id not in {t['id'] for t in library()}: raise ValueError('Track not found')
    if any(j['status']=='downloading' and track_id.startswith(j.get('video_id','!')) for j in jobs.values()): raise ValueError('Wait for this download to finish')
    # Only files sharing the validated metadata stem belong to this track.
    for file in DATA.glob(track_id+'.*'):
        if file.is_file(): file.unlink()
    items=playlists()
    for item in items: item['tracks']=[t for t in item['tracks'] if t!=track_id]
    save_playlists(items)

def download(key, url, kind):
    with lock: jobs[key].update(status='downloading',kind=kind,title=url)
    try:
        args = downloader_command() + ['--ignore-config','--no-playlist','--no-overwrites','--write-info-json','--newline','--restrict-filenames','-o',str(DATA / ('%(id)s-'+kind+'.%(ext)s'))]
        args += ['-x','--audio-format','mp3']
        ffmpeg = binary('ffmpeg')
        binary('ffprobe')
        args += ['--ffmpeg-location', str(pathlib.Path(ffmpeg).parent)]
        try: args += ['--js-runtimes', 'deno:'+binary('deno')]
        except FileNotFoundError: pass
        process = subprocess.Popen(args + ['--',url], **subprocess_options())
        tail = ''
        for line in process.stdout:
            tail = line.strip()
            with lock: jobs[key]['detail'] = tail[-400:]
        code = process.wait()
        with lock:
            jobs[key]['status'] = 'complete' if code == 0 else 'failed'
            jobs[key]['detail'] = 'Added to your library' if code == 0 else tail
    except OSError as e:
        with lock: jobs[key].update(status='failed',detail=str(e))

DEFAULT_SETTINGS={'palette':'sage','layout':'grid','adblock':True,'insights':True}
PALETTES={'sage','violet','ocean','rose','amber','mono'}
def read_settings():
    file=DATA/'settings.json'
    return {**DEFAULT_SETTINGS,**(json.loads(file.read_text()) if file.exists() else {})}
def update_settings(body):
    value=read_settings()
    if body.get('palette',value['palette']) not in PALETTES: raise ValueError('Unknown palette')
    if body.get('layout',value['layout']) not in ('grid','list','compact'): raise ValueError('Unknown layout')
    for key in ('adblock','insights'):
        if key in body and not isinstance(body[key],bool): raise ValueError('Invalid setting')
    value.update({k:body[k] for k in DEFAULT_SETTINGS if k in body})
    temp=DATA/'settings.tmp';temp.write_text(json.dumps(value));temp.replace(DATA/'settings.json');return value

def stats_db():
    db=sqlite3.connect(DATA/'listening.sqlite')
    db.execute('CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, track TEXT, seconds REAL DEFAULT 0, played INTEGER DEFAULT 0, sequence INTEGER DEFAULT 0)')
    db.execute('CREATE TABLE IF NOT EXISTS days (day TEXT PRIMARY KEY, seconds REAL DEFAULT 0)')
    return db

def record_listen(body):
    sid=body.get('session','');track=body.get('track');seconds=body.get('seconds');seq=body.get('sequence');day=body.get('day','')
    if not isinstance(sid,str) or not re.fullmatch(r'[A-Za-z0-9-]{8,64}',sid): raise ValueError('Invalid listening session')
    if not isinstance(seconds,(float,int)) or isinstance(seconds,bool) or not math.isfinite(seconds) or not 0<seconds<=15: raise ValueError('Invalid listening duration')
    if not isinstance(seq,int) or isinstance(seq,bool) or seq<1: raise ValueError('Invalid sequence')
    try: date=datetime.date.fromisoformat(day)
    except (ValueError,TypeError): raise ValueError('Invalid date')
    if abs((date-datetime.datetime.now(datetime.timezone.utc).date()).days)>1: raise ValueError('Invalid listening date')
    item=next((t for t in library() if t['id']==track),None)
    if not item: raise ValueError('Track not found')
    threshold=min(30,max(1,float(item['duration'] or 60)/2))
    db=stats_db()
    try:
        with db:
            db.execute('INSERT OR IGNORE INTO sessions(id,track) VALUES (?,?)',(sid,track))
            old=db.execute('SELECT track,seconds,sequence FROM sessions WHERE id=?',(sid,)).fetchone()
            if old[0]!=track: raise ValueError('Session track mismatch')
            if seq<=old[2]: return {'ok':True}
            total=old[1]+seconds
            db.execute('UPDATE sessions SET seconds=?,played=?,sequence=? WHERE id=?',(total,int(total>=threshold),seq,sid))
            db.execute('INSERT INTO days(day,seconds) VALUES (?,?) ON CONFLICT(day) DO UPDATE SET seconds=seconds+excluded.seconds',(day,seconds))
        return {'ok':True}
    finally: db.close()

def insights():
    db=stats_db()
    try:
        totals=db.execute('SELECT COALESCE(SUM(seconds),0),COALESCE(SUM(played),0) FROM sessions').fetchone()
        top=db.execute('SELECT track,SUM(seconds),SUM(played) FROM sessions GROUP BY track ORDER BY SUM(played) DESC,SUM(seconds) DESC').fetchall()
        days=db.execute('SELECT day,seconds FROM days ORDER BY day DESC LIMIT 30').fetchall()
    finally: db.close()
    items={t['id']:t for t in library()};leaders=[];artists={}
    for tid,seconds,plays in top:
        if tid in items:
            item=items[tid];leaders.append({**item,'seconds':seconds,'plays':plays})
            artists[item['artist']]=artists.get(item['artist'],0)+seconds
    artist=max(artists,key=artists.get) if artists else None
    return {'seconds':totals[0],'plays':totals[1],'unique_tracks':len(leaders),'top_artist':artist,'leaders':leaders[:5],'days':[{'day':d,'seconds':t} for d,t in reversed(days)]}

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        import logging
        logging.getLogger('aural.http').debug(format, *args)
    def reply(self, value, status=200):
        body=json.dumps(value).encode(); self.send_response(status); self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def do_POST(self):
        if self.headers.get('Origin') not in (None, f'http://127.0.0.1:{self.server.server_port}', f'http://localhost:{self.server.server_port}'):
            return self.reply({'error':'Origin rejected'},403)
        try:
            size=int(self.headers.get('Content-Length',0))
            if size <= 0 or size > 4096: raise ValueError('Invalid request size')
            body=json.loads(self.rfile.read(size))
            if not isinstance(body,dict): raise ValueError('Invalid request')
            with lock:
                if self.path=='/api/settings': return self.reply(update_settings(body))
                if self.path=='/api/listen': return self.reply(record_listen(body))
                if self.path=='/api/favorites':
                    ids=body.get('tracks',[])
                    if not isinstance(ids,list) or not all(isinstance(t,str) for t in ids): raise ValueError('Invalid favorites')
                    valid={t['id'] for t in library()};temp=DATA/'favorites.tmp';temp.write_text(json.dumps([t for t in dict.fromkeys(ids) if t in valid]));temp.replace(DATA/'favorites.json');return self.reply({'ok':True})
                if self.path=='/api/playlists': return self.reply(edit_playlist(body))
                if self.path=='/api/remove':
                    delete_track(body.get('id'));return self.reply({'ok':True})
                if self.path!='/api/download': return self.reply({'error':'Not found'},404)
                url=body.get('url','');kind=body.get('kind','audio');vid=video_id(url)
                if kind!='audio': raise ValueError('Aural supports audio downloads only')
                stem=vid+'-'+kind
                if any(t['id']==stem for t in library()): raise ValueError('This '+kind+' is already in your library')
                if any(j['status']=='downloading' and j.get('video_id')==vid and j['kind']==kind for j in jobs.values()): raise ValueError('This download is already in progress')
                if sum(j['status']=='downloading' for j in jobs.values())>=3: raise ValueError('Three downloads are already running')
                key=uuid.uuid4().hex;jobs[key]=dict(id=key,status='downloading',kind=kind,title=url,video_id=vid)
            threading.Thread(target=download,args=(key,'https://www.youtube.com/watch?v='+vid,kind),daemon=True).start();self.reply({'id':key},202)
        except (ValueError,TypeError,AttributeError) as e: self.reply({'error':str(e)},400)
        except OSError: self.reply({'error':'Could not update local storage'},500)
    def do_GET(self):
        path=unquote(urlparse(self.path).path)
        if path == '/api/settings':
            with lock: return self.reply(read_settings())
        if path == '/api/insights':
            with lock: return self.reply(insights())
        if path == '/api/favorites':
            with lock: return self.reply(json.loads((DATA/'favorites.json').read_text()) if (DATA/'favorites.json').exists() else [])
        if path == '/api/playlists':
            with lock: return self.reply(playlists())
        if path == '/api/library':
            with lock: return self.reply(library())
        if path == '/api/jobs':
            with lock: return self.reply(list(jobs.values()))
        if path.startswith('/media/'):
            file=DATA / pathlib.Path(path).name
            if file.suffix not in ('.mp3','.m4a','.opus','.webm','.mp4','.mkv'): return self.reply({'error':'Not found'},404)
        elif re.fullmatch(r'/icons/[a-z0-9-]+\.svg',path): file=ROOT/'static'/path.lstrip('/')
        else: file=ROOT / 'static' / ('index.html' if path == '/' else pathlib.Path(path).name)
        if not file.is_file(): return self.reply({'error':'Not found'},404)
        size=file.stat().st_size; start=0; end=size-1
        match=re.fullmatch(r'bytes=(\d+)-(\d*)',self.headers.get('Range',''))
        if match:
            start=int(match[1]); end=min(int(match[2]) if match[2] else end,end)
            if start> end:
                self.send_response(416);self.send_header('Content-Range',f'bytes */{size}');self.end_headers();return
        self.send_response(206 if match else 200);self.send_header('Content-Type',mimetypes.guess_type(file.name)[0] or 'application/octet-stream');self.send_header('Accept-Ranges','bytes');self.send_header('Content-Length',str(end-start+1))
        if match:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
        self.end_headers()
        try:
            with file.open('rb') as f:
                f.seek(start);remaining=end-start+1
                while remaining:
                    chunk=f.read(min(65536,remaining))
                    if not chunk:break
                    self.wfile.write(chunk);remaining-=len(chunk)
        except (BrokenPipeError,ConnectionResetError):pass
if __name__ == '__main__':
    print('Aural is running at http://127.0.0.1:8765',flush=True)
    ThreadingHTTPServer(('127.0.0.1',8765),Handler).serve_forever()
