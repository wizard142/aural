import json
import tempfile
import threading
import io
import hashlib
from urllib.error import URLError
import unittest
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import song_metadata as metadata
import song_identification as identification
import ai_playlists as ai
import audio_analysis
from song_enrichment import Enricher

class SongProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        (self.root/'a-audio.info.json').write_text(json.dumps({'title':'Song','artist':'Singer','duration':200}))
        (self.root/'a-audio.mp3').write_bytes(b'fixture')
        self.track={'id':'a-audio','title':'Song','artist':'Singer','duration':200,'file':'a-audio.mp3'}
    def tearDown(self):self.temp.cleanup()
    def test_corrections_survive_metadata_refresh_and_are_prioritized(self):
        profile=metadata.update_labels(self.root,'a-audio',{'moods':['Sad','sad'],'genres':['metal'],'excluded_moods':['happy'],'energy':'low','note':'Feels sad to me'})
        profile['audio_analysis']={'mood_scores':{'happy':.99},'genres':[{'label':'Pop','score':.9}]};profile['audio_analyzed']=True
        profile['identification']={'status':'matched','title':'Recording','artist':'Artist','genres':['pop']}
        profile['fingerprint']={'fingerprint':'PRIVATE-FINGERPRINT'}
        metadata.save_profile(self.root,'a-audio',profile)
        refreshed=metadata.capture_profile(self.root,'a-audio')
        self.assertTrue(refreshed['audio_analyzed']);self.assertEqual(refreshed['user_labels']['moods'],['sad'])
        catalog=ai.build_catalog([self.track],{'a-audio':refreshed},'sad',{'provider':'groq'})
        self.assertEqual(catalog[0]['user_labels']['excluded_moods'],['happy']);self.assertEqual(catalog[0]['identification']['title'],'Recording')
        self.assertNotIn('PRIVATE-FINGERPRINT',json.dumps(catalog))
    def test_invalid_corrections_and_explicit_clear(self):
        for body in ({'moods':['sad'],'excluded_moods':['sad']},{'moods':'sad'},{'energy':'nonsense'},{'note':'a'*301}):
            with self.assertRaises(ValueError):metadata.update_labels(self.root,'a-audio',body)
        metadata.update_labels(self.root,'a-audio',{'moods':['sad']})
        self.assertEqual(metadata.update_labels(self.root,'a-audio',{})['user_labels']['moods'],[])
    def test_background_merge_preserves_corrections(self):
        started=threading.Event();finish=threading.Event();lock=threading.RLock()
        worker=Enricher(self.root,lock,lambda:[self.track],lambda:{})
        def analyze(*args):
            started.set();self.assertTrue(finish.wait(3));return {'version':'effnet-mood-v1','mood_scores':{'sad':.9}}
        with patch('audio_analysis.analyze',side_effect=analyze):
            job=worker.submit([self.track]);self.assertTrue(started.wait(3))
            with lock:metadata.update_labels(self.root,'a-audio',{'moods':['happy']})
            finish.set();worker.queue.join()
        profile=metadata.read_profile(self.root,'a-audio')
        self.assertEqual(profile['user_labels']['moods'],['happy']);self.assertTrue(profile['audio_analyzed']);self.assertEqual(worker.jobs[job]['status'],'complete')
    def test_deleted_song_is_not_resurrected_by_background_worker(self):
        started=threading.Event();finish=threading.Event();lock=threading.RLock();tracks=[self.track]
        worker=Enricher(self.root,lock,lambda:tracks,lambda:{})
        def analyze(*args):started.set();finish.wait(3);return {'version':'effnet-mood-v1'}
        with patch('audio_analysis.analyze',side_effect=analyze):
            worker.submit(tracks);self.assertTrue(started.wait(3))
            with lock:
                tracks.clear()
                for file in self.root.iterdir():file.unlink()
            finish.set();worker.queue.join()
        self.assertFalse(list(self.root.iterdir()))

class FingerprintMatchTests(unittest.TestCase):
    def response(self,score=.95,title='Song',duration=200):
        return {'status':'ok','results':[{'score':score,'recordings':[{'id':'12345678-1234-1234-1234-123456789abc','title':title,'duration':duration,'artists':[{'name':'Singer'}]}]}]}
    def test_strong_match_and_unknown_recordings(self):
        self.assertEqual(identification.select_match(self.response(),200)['status'],'matched')
        self.assertEqual(identification.select_match(self.response(.5),200)['status'],'ambiguous')
        self.assertEqual(identification.select_match(self.response(duration=350),200)['status'],'unmatched')
    def test_conflicting_matches_are_not_applied(self):
        response=self.response();other=self.response(.94,'Different')['results'][0];other['recordings'][0]['id']='22345678-1234-1234-1234-123456789abc';response['results'].append(other)
        self.assertEqual(identification.select_match(response,200)['status'],'ambiguous')
    def test_lookup_sends_fingerprint_only_and_keeps_metadata_provenance(self):
        fp={'duration':200,'fingerprint':'abc'}
        with patch.object(ai,'get_key',return_value='fixture-client'),patch.object(identification,'request_json',side_effect=[self.response(),{'title':'Confirmed','artist-credit':[{'name':'Singer'}],'genres':[{'name':'metal','count':2}]}]) as request:
            _,result=identification.identify('ignored',fp)
        payload=request.call_args_list[0].args[1].decode();self.assertIn('fingerprint=abc',payload);self.assertNotIn('ignored',payload)
        self.assertEqual(result['genres'],['metal']);self.assertEqual(result['title'],'Confirmed')

class ModelDownloadTests(unittest.TestCase):
    def test_transient_failure_retries_and_verifies_hash(self):
        payload=b'fixture model'
        entry={'name':'test.onnx','url':'https://example.org/test.onnx','size':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}
        with tempfile.TemporaryDirectory() as temp,patch.object(audio_analysis,'manifest',return_value={'files':[entry]}),patch.object(audio_analysis,'models_directory',return_value=Path(temp)),patch.object(audio_analysis,'urlopen',side_effect=[URLError('temporary'),io.BytesIO(payload)]) as request,patch.object(audio_analysis.time,'sleep'):
            audio_analysis.ensure_models(temp)
            self.assertEqual((Path(temp)/'test.onnx').read_bytes(),payload);self.assertEqual(request.call_count,2)
    def test_invalid_model_is_never_installed(self):
        entry={'name':'test.onnx','url':'https://example.org/test.onnx','size':4,'sha256':hashlib.sha256(b'good').hexdigest()}
        with tempfile.TemporaryDirectory() as temp,patch.object(audio_analysis,'manifest',return_value={'files':[entry]}),patch.object(audio_analysis,'models_directory',return_value=Path(temp)),patch.object(audio_analysis,'urlopen',return_value=io.BytesIO(b'evil')):
            with self.assertRaisesRegex(ValueError,'checksum'):audio_analysis.ensure_models(temp)
            self.assertFalse((Path(temp)/'test.onnx').exists());self.assertFalse(list(Path(temp).glob('*.download')))

if __name__=='__main__':unittest.main()
