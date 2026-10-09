"""Fingerprint lookup; source identity stays separate from source and user labels."""
import json
import re
import subprocess
import threading
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from runtime import binary, subprocess_options
import ai_playlists

KEY_CONFIG={'provider':'compatible','endpoint':'https://api.acoustid.org/v2/lookup'}
RATE_LOCK=threading.Lock();LAST_REQUEST={}
USER_AGENT='Aural/1.2 (https://github.com/wizard142/aural)'

def fingerprint(media):
    run=subprocess.run([binary('fpcalc'),'-json',str(media)],timeout=90,**subprocess_options())
    # fpcalc can report decoder EOF after printing a complete fingerprint.
    try:result=json.loads(run.stdout)
    except ValueError:raise ValueError('Could not fingerprint this song') from None
    if not result.get('fingerprint') or not result.get('duration'):raise ValueError('This song has no usable audio fingerprint')
    return {'duration':float(result['duration']),'fingerprint':result['fingerprint']}

def request_json(url,data=None,service='musicbrainz'):
    with RATE_LOCK:
        delay=(1.1 if service=='musicbrainz' else .4)-(time.monotonic()-LAST_REQUEST.get(service,0))
        if delay>0:time.sleep(delay)
        LAST_REQUEST[service]=time.monotonic()
    headers={'User-Agent':USER_AGENT,'Accept':'application/json'}
    if data is not None:headers['Content-Type']='application/x-www-form-urlencoded'
    try:
        with urlopen(Request(url,data,headers),timeout=30) as response:raw=response.read(2_000_001)
        if len(raw)>2_000_000:raise ValueError('Identification response was too large')
        return json.loads(raw)
    except HTTPError as error:
        code=error.code;error.close()
        raise ValueError('Identification service rejected the request (HTTP '+str(code)+'). Check your AcoustID application key or try later.') from None
    except (URLError,TimeoutError,ValueError) as error:
        raise ValueError('Could not reach or read the identification service. Try again later.') from None

def select_match(response,duration):
    if response.get('status')!='ok':raise ValueError('AcoustID rejected the application key or fingerprint')
    candidates=[]
    for result in response.get('results',[]):
        for recording in result.get('recordings',[]):
            mbid=recording.get('id','')
            if not re.fullmatch(r'[0-9a-f-]{36}',mbid):continue
            actual=recording.get('duration')
            if actual and abs(actual-duration)>max(15,duration*.08):continue
            candidates.append({'recording_id':mbid,'score':float(result.get('score',0)),'title':str(recording.get('title',''))[:300],'artist':', '.join(str(a.get('name','')) for a in recording.get('artists',[]))[:300],'album':next((str(r.get('title',''))[:300] for r in recording.get('releasegroups',[]) if r.get('title')),'')})
    unique={}
    for item in sorted(candidates,key=lambda x:x['score'],reverse=True):unique.setdefault(item['recording_id'],item)
    candidates=list(unique.values())[:5]
    if not candidates:return {'status':'unmatched','basis':'AcoustID fingerprint lookup','candidates':[]}
    best=candidates[0]
    competing=[c for c in candidates[1:] if (c['title'].casefold(),c['artist'].casefold())!=(best['title'].casefold(),best['artist'].casefold())]
    if best['score']<.8 or (competing and best['score']-competing[0]['score']<.05):
        return {'status':'ambiguous','basis':'AcoustID fingerprint lookup; no identity applied','candidates':candidates}
    return {**best,'status':'matched','basis':'AcoustID fingerprint match + MusicBrainz metadata','candidates':candidates}

def identify(media,cached_fingerprint=None):
    key=ai_playlists.get_key(KEY_CONFIG)
    if not key:raise ValueError('Add an AcoustID application key in Settings → Song profiles first')
    fp=cached_fingerprint or fingerprint(media)
    data=urlencode({'client':key,'duration':round(fp['duration']),'fingerprint':fp['fingerprint'],'meta':'recordings releasegroups','format':'json'}).encode()
    match=select_match(request_json(KEY_CONFIG['endpoint'],data,'acoustid'),fp['duration'])
    if match['status']=='matched':
        url='https://musicbrainz.org/ws/2/recording/'+match['recording_id']+'?'+urlencode({'fmt':'json','inc':'genres+artist-credits+releases'})
        try:
            info=request_json(url)
            match['title']=str(info.get('title') or match['title'])[:300]
            match['artist']=''.join(str(a.get('name') or a.get('artist',{}).get('name',''))+str(a.get('joinphrase','')) for a in info.get('artist-credit',[]))[:300] or match['artist']
            match['genres']=[str(g['name'])[:100] for g in sorted(info.get('genres',[]),key=lambda g:g.get('count',0),reverse=True) if g.get('name')][:8]
            match['album']=match['album'] or next((str(r['title'])[:300] for r in info.get('releases',[]) if r.get('title')),'')
        except ValueError:match['metadata_warning']='Fingerprint matched; MusicBrainz metadata could not be fetched. Retry identification later.'
    return fp,match
