"""Fetch verified Windows x64 FFmpeg and Deno bundles for Aural."""
import hashlib
import json
import os
from urllib.parse import urlparse
from pathlib import Path
import shutil
import tempfile
from urllib.request import Request, urlopen
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[2]
BIN=ROOT/'vendor'/'bin'
NOTICES=ROOT/'vendor'/'notices'

def request(url):
    headers={'User-Agent':'Aural-build/1.0'}
    token=os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if token and urlparse(url).hostname=='api.github.com':headers['Authorization']='Bearer '+token
    return Request(url,headers=headers)

def fetch(url, target):
    req=request(url)
    with urlopen(req,timeout=120) as response, target.open('wb') as output:
        shutil.copyfileobj(response,output)

def read(url):
    with urlopen(request(url),timeout=60) as response:
        return response.read().decode('utf-8')

def checked_download(url, expected, target):
    fetch(url,target)
    actual=hashlib.sha256(target.read_bytes()).hexdigest()
    if actual.lower()!=expected.lower():
        target.unlink(missing_ok=True)
        raise RuntimeError('SHA-256 verification failed for '+url)
    return actual

def main():
    BIN.mkdir(parents=True,exist_ok=True);NOTICES.mkdir(parents=True,exist_ok=True)
    manifest={}
    with tempfile.TemporaryDirectory(prefix='aural-tools-') as scratch:
        scratch=Path(scratch)
        ffurl='https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip'
        checksum=read(ffurl+'.sha256').strip().split()[0]
        archive=scratch/'ffmpeg.zip'
        manifest['ffmpeg']={'url':ffurl,'sha256':checked_download(ffurl,checksum,archive),'version':read(ffurl+'.ver').strip(),'source':'https://www.gyan.dev/ffmpeg/builds/'}
        with ZipFile(archive) as zipfile:
            for name in ('ffmpeg.exe','ffprobe.exe'):
                matches=[i for i in zipfile.infolist() if i.filename.endswith('/bin/'+name)]
                if len(matches)!=1:raise RuntimeError('Missing '+name+' in FFmpeg archive')
                (BIN/name).write_bytes(zipfile.read(matches[0]))
            for item in zipfile.infolist():
                name=Path(item.filename).name
                if name.lower().startswith(('license','readme')) and not item.is_dir():
                    (NOTICES/('ffmpeg-'+name)).write_bytes(zipfile.read(item))
        release=json.loads(read('https://api.github.com/repos/denoland/deno/releases/latest'))
        asset=next(a for a in release['assets'] if a['name']=='deno-x86_64-pc-windows-msvc.zip')
        digest=asset.get('digest','')
        if not digest.startswith('sha256:'):raise RuntimeError('Deno release does not provide a SHA-256 digest')
        archive=scratch/'deno.zip'
        manifest['deno']={'url':asset['browser_download_url'],'version':release['tag_name'],'sha256':checked_download(asset['browser_download_url'],digest[7:],archive)}
        with ZipFile(archive) as zipfile:(BIN/'deno.exe').write_bytes(zipfile.read('deno.exe'))
        fetch('https://raw.githubusercontent.com/denoland/deno/'+release['tag_name']+'/LICENSE.md',NOTICES/'deno-LICENSE.md')
    (NOTICES/'tool-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('Verified Windows FFmpeg, ffprobe and Deno prepared in',BIN)
if __name__=='__main__':main()
