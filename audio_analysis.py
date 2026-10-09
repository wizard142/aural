"""Local sampled-audio inference. Model scores are estimates, never accuracy claims."""
import hashlib
import json
import subprocess
import threading
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError
from runtime import APP_ROOT, binary, subprocess_options

MODEL_LOCK=threading.Lock()
SESSIONS={}
VERSION='effnet-mood-v1'

def manifest():return json.loads((APP_ROOT/'model-assets.json').read_text(encoding='utf-8'))
def models_directory(data):
    bundled=APP_ROOT/'vendor'/'models'
    return bundled if all((bundled/f['name']).is_file() for f in manifest()['files']) else Path(data)/'models'

def ensure_models(data,progress=lambda text:None):
    with MODEL_LOCK:
        directory=models_directory(data);directory.mkdir(parents=True,exist_ok=True)
        for entry in manifest()['files']:
            file=directory/entry['name']
            if file.exists() and hashlib.sha256(file.read_bytes()).hexdigest()==entry['sha256']:continue
            progress('Downloading audio models…')
            temp=file.with_suffix(file.suffix+'.download')
            try:
                for attempt in range(3):
                    try:
                        with urlopen(Request(entry['url'],headers={'User-Agent':'Aural/1.2 (https://github.com/wizard142/aural)'}),timeout=30) as response,temp.open('wb') as output:
                            remaining=entry['size'];digest=hashlib.sha256()
                            while chunk:=response.read(65536):
                                remaining-=len(chunk)
                                if remaining<0:raise ValueError('Audio model download has an unexpected size')
                                digest.update(chunk);output.write(chunk)
                        break
                    except (URLError,TimeoutError):
                        if attempt==2:raise ValueError('Could not download audio models. Check your connection and try analysis again.') from None
                        progress('Retrying audio model download…');time.sleep(attempt+1)
                if remaining or digest.hexdigest()!=entry['sha256']:raise ValueError('Audio model checksum failed; please try again')
                temp.replace(file)
            finally:temp.unlink(missing_ok=True)
        (directory/'LICENSE.txt').write_text('Essentia / Music Technology Group, Universitat Pompeu Fabra\nCC BY-NC-SA 4.0: https://creativecommons.org/licenses/by-nc-sa/4.0/\nSource: https://essentia.upf.edu/models.html\n',encoding='utf-8')
    return directory

def session(file):
    import onnxruntime as ort
    ort.disable_telemetry_events()
    name=str(file)
    if name not in SESSIONS:
        options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
        SESSIONS[name]=ort.InferenceSession(name,sess_options=options,providers=['CPUExecutionProvider'])
    return SESSIONS[name]

def mel_patches(audio):
    """16 kHz, 512-point Hann power spectrum, 96 Slaney bands, 128-frame patches.

    Parameters follow TensorflowInputMusiCNN and EffnetDiscogs model documentation.
    Implementation uses NumPy; no Essentia library code is bundled.
    """
    import numpy as np
    padded=np.pad(audio,(256,256))
    frames=np.lib.stride_tricks.sliding_window_view(padded,512)[::256]
    power=np.abs(np.fft.rfft(frames*np.hanning(512),axis=1))**2
    # Slaney's piecewise linear/log mel scale and unit-area triangular filters.
    maxmel=15+np.log(8000/1000)/np.log(6.4)*27
    mels=np.linspace(0,maxmel,98)
    edges=np.where(mels<15,mels*200/3,1000*np.exp((mels-15)*np.log(6.4)/27))
    frequencies=np.linspace(0,8000,257)
    bank=np.maximum(0,np.minimum((frequencies[None,:]-edges[:-2,None])/(edges[1:-1]-edges[:-2])[:,None],(edges[2:,None]-frequencies[None,:])/(edges[2:]-edges[1:-1])[:,None]))
    bank*=2/(edges[2:]-edges[:-2])[:,None]
    mel=np.log10(1+10000*(power@bank.T)).astype(np.float32)
    if len(mel)<128:mel=np.pad(mel,((0,128-len(mel)),(0,0)),mode='edge')
    return np.stack([mel[i:i+128] for i in range(0,len(mel)-127,62)])

def decode_sample(media,start,seconds=8):
    import numpy as np
    options=subprocess_options();options.update(text=False);options.pop('encoding');options.pop('errors');options['stderr']=subprocess.PIPE
    run=subprocess.run([binary('ffmpeg'),'-v','error','-ss',str(start),'-i',str(media),'-t',str(seconds),'-ac','1','-ar','16000','-f','f32le','pipe:1'],timeout=45,**options)
    if run.returncode:raise ValueError('Could not decode this song for audio analysis')
    return np.frombuffer(run.stdout,dtype='<f4').copy()

def analyze(media,duration,data,progress=lambda text:None):
    import numpy as np
    directory=ensure_models(data,progress);progress('Analyzing audio locally…')
    duration=float(duration or 0)
    if duration<=0:
        options=subprocess_options()
        run=subprocess.run([binary('ffprobe'),'-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(media)],timeout=20,**options)
        try:duration=float(run.stdout.strip())
        except ValueError:raise ValueError('Could not determine this song’s duration') from None
    positions=sorted({round(max(0,min(duration-8,duration*f)),2) for f in (.15,.45,.75)})
    samples=[];patches=[]
    for start in positions:
        audio=decode_sample(media,start)
        if len(audio)>=512 and float(np.sqrt(np.mean(audio**2)))>1e-5:
            samples.append(audio);patches.extend(mel_patches(audio))
    if not patches:raise ValueError('No audible audio was found in the sampled sections')
    extractor=session(directory/'discogs-effnet-bsdynamic-1.onnx')
    genre_predictions=[];embeddings=[]
    for offset in range(0,len(patches),8):
        batch=np.asarray(patches[offset:offset+8],dtype=np.float32)
        outputs=extractor.run(None,{extractor.get_inputs()[0].name:batch})
        for out,values in zip(extractor.get_outputs(),outputs):
            if values.shape[-1]==400:genre_predictions.extend(values)
            elif values.shape[-1]==1280:embeddings.extend(values)
    if not embeddings or not genre_predictions:raise ValueError('Audio model returned an unsupported output')
    scores={}
    for mood in ('sad','happy','relaxed','aggressive'):
        stem='mood_'+mood+'-discogs-effnet-1'
        info=json.loads((directory/(stem+'.json')).read_text());head=session(directory/(stem+'.onnx'))
        output=next(o.name for o in head.get_outputs() if o.shape[-1]==2)
        values=head.run([output],{head.get_inputs()[0].name:np.asarray(embeddings,dtype=np.float32)})[0]
        scores[mood]=round(float(np.mean(values,axis=0)[info['classes'].index(mood)]),3)
    genres=np.mean(genre_predictions,axis=0)
    labels=json.loads((directory/'discogs-effnet-bsdynamic-1.json').read_text())['classes']
    ranked=[{'label':labels[int(i)].replace('---',' / '),'score':round(float(genres[i]),3)} for i in np.argsort(genres)[-5:][::-1]]
    rms=float(np.mean([np.sqrt(np.mean(sample**2)) for sample in samples]))
    # A rough onset periodicity estimate; half/double-tempo ambiguity remains.
    bpms=[]
    for sample in samples:
        envelope=np.sqrt(np.mean(sample[:len(sample)//256*256].reshape(-1,256)**2,axis=1))
        onset=np.maximum(0,np.diff(envelope));onset-=np.mean(onset)
        ac=np.correlate(onset,onset,mode='full')[len(onset)-1:]
        low,high=int(60*62.5/180),int(60*62.5/60)
        if len(ac)>high and ac[0]>1e-8:bpms.append(60*62.5/(low+int(np.argmax(ac[low:high+1]))))
    return {'version':VERSION,'basis':'Local audio model estimates from sampled sections; not verified labels','model':'MTG Discogs Effnet + mood classifiers','sample_positions_seconds':positions,'sample_seconds':sum(len(x) for x in samples)/16000,'mood_scores':scores,'genres':ranked,'energy':'high' if rms>.18 else 'medium' if rms>.07 else 'low','energy_basis':'sample RMS loudness; affected by mastering','tempo_bpm_estimate':round(float(np.median(bpms)),1) if bpms else None}

if __name__=='__main__':
    import sys
    print(ensure_models(Path(sys.argv[1]) if len(sys.argv)>1 else APP_ROOT/'vendor'))
