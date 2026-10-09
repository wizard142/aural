"""Offline real-model checks with generated audio; never submits audio or fingerprints."""
from pathlib import Path
import tempfile
import wave
import numpy as np
import audio_analysis
import song_identification

def run():
    with tempfile.TemporaryDirectory(prefix='aural-audio-check-') as temp:
        root=Path(temp);file=root/'fixture.wav';rate=16000
        t=np.arange(rate*20)/rate
        chord=sum(np.sin(2*np.pi*f*t) for f in (261.63,329.63,392.0))/3
        pulses=.35+.65*np.maximum(0,np.sin(2*np.pi*2*t))
        samples=(chord*pulses*.35*32767).astype('<i2')
        with wave.open(str(file),'wb') as out:
            out.setnchannels(1);out.setsampwidth(2);out.setframerate(rate);out.writeframes(samples.tobytes())
        result=audio_analysis.analyze(file,20,root)
        assert len(result['sample_positions_seconds'])==3
        assert result['sample_seconds']>=20
        assert all(np.isfinite(v) and 0<=v<=1 for v in result['mood_scores'].values())
        assert len(result['genres'])==5 and all(0<=g['score']<=1 for g in result['genres'])
        fp=song_identification.fingerprint(file)
        assert fp['duration']>=19 and len(fp['fingerprint'])>30
        return {'real_local_audio_inference':True,'real_local_audio_fingerprint':True}

if __name__=='__main__':print(run())
