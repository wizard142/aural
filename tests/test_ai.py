import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ai_playlists as ai
import song_metadata as metadata

class ProviderTests(unittest.TestCase):
    def tearDown(self):ai.clear_session_keys()
    def config(self,name):return ai.validate_config({'provider':name,'model':'test-model','endpoint':'https://example.com/v1/chat/completions'})
    def test_native_and_compatible_payloads(self):
        for name in ai.PROVIDERS:
            config=self.config(name);url,headers,body=ai.request_payload(config,'test-key','prompt')
            self.assertTrue(url.startswith('https://'));self.assertNotIn('test-key',url);self.assertNotIn('test-key',json.dumps(body))
            if name=='anthropic':self.assertEqual(headers['x-api-key'],'test-key');self.assertIn('system',body)
            elif name=='gemini':self.assertEqual(headers['x-goog-api-key'],'test-key');self.assertTrue(url.endswith(':generateContent'))
            else:self.assertEqual(headers['Authorization'],'Bearer test-key')
            if name=='openai':self.assertFalse(body['store']);self.assertEqual(body['text']['format']['type'],'json_object')
    def test_all_response_adapters(self):
        text=json.dumps({'name':'Test','track_ids':['a']})
        for name in ai.PROVIDERS:
            kind=ai.PROVIDERS[name]['kind']
            data={'output':[{'content':[{'type':'output_text','text':text}]}]} if kind=='responses' else {'content':[{'type':'text','text':text}]} if kind=='anthropic' else {'candidates':[{'content':{'parts':[{'text':text}]}}]} if kind=='gemini' else {'choices':[{'message':{'content':text}}]}
            self.assertEqual(ai.parse_result(ai.extract_text(self.config(name),data))['track_ids'],['a'])
    def test_invalid_ids_and_duplicates_rejected(self):
        for ids in (['missing'],['a','a'],[]):
            with self.assertRaises(ValueError):ai.validate_result({'track_ids':ids},{'a'})
        result=ai.validate_result({'track_ids':['b','a'],'name':'A'*90},{'a','b'});self.assertEqual(result['tracks'],['b','a']);self.assertEqual(len(result['name']),60)
    def test_temporary_secret_fallback_and_scope(self):
        config=self.config('openai')
        with patch.object(ai,'secure_backend',return_value=None):
            warning=ai.set_key(config,'test-key',True);self.assertIn('not saved',warning);self.assertEqual(ai.get_key(config),'test-key');ai.forget_key(config);self.assertNotIn(ai.account(config),ai.SESSION_KEYS)
        other=self.config('compatible');other2=dict(other,endpoint='https://another.example/v1/chat/completions');self.assertNotEqual(ai.account(other),ai.account(other2))
    def test_remembered_key_survives_new_session_and_reports_storage(self):
        config=self.config('groq');stored={}
        backend=MagicMock()
        backend.set_password.side_effect=lambda service,ident,value:stored.update({ident:value})
        backend.get_password.side_effect=lambda service,ident:stored.get(ident)
        backend.delete_password.side_effect=lambda service,ident:stored.pop(ident,None)
        with patch.object(ai,'secure_backend',return_value=backend):
            self.assertIsNone(ai.set_key(config,'test-key',True))
            self.assertEqual(ai.key_status(config),{'has_key':True,'key_saved':True,'key_source':'secure'})
            ai.clear_session_keys()
            self.assertEqual(ai.get_key(config),'test-key')
            self.assertTrue(ai.key_status(config)['key_saved'])
            ai.forget_key(config)
            self.assertFalse(ai.key_status(config)['has_key'])
    def test_failed_secure_save_is_explicit_and_session_only(self):
        config=self.config('groq');backend=MagicMock();backend.get_password.return_value=None
        with patch.object(ai,'secure_backend',return_value=backend):
            self.assertIn('could not confirm',ai.set_key(config,'test-key',True))
            self.assertEqual(ai.key_status(config),{'has_key':True,'key_saved':False,'key_source':'session'})
    def test_no_redirects_or_key_in_prompt(self):
        config=self.config('openai');ai.SESSION_KEYS[ai.account(config)]='test-key'
        response=MagicMock();response.__enter__.return_value=response;response.read.return_value=json.dumps({'output':[{'content':[{'type':'output_text','text':'{"track_ids":["a"]}'}]}]}).encode()
        opener=MagicMock();opener.open.return_value=response
        with patch.object(ai,'build_opener',return_value=opener):self.assertEqual(ai.call_provider(config,'song metadata')['track_ids'],['a'])
        request=opener.open.call_args.args[0];self.assertNotIn('test-key',request.data.decode());self.assertIsNone(ai.NoRedirect().redirect_request(None,None,302,'',{},'https://other.example'))
    def test_profile_provenance_and_missing_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            file=Path(temp)/'a.info.json';file.write_text(json.dumps({'title':'Unknown title','artist':'Artist','tags':['jazz'],'description':'Instrumental jazz','genre':'Jazz','album':'Album'}))
            result=metadata.capture_profile(temp,'a');self.assertEqual(result['facts']['album'],'Album');self.assertEqual(result['facts']['genres_reported'],['Jazz']);self.assertIn('jazz',result['genre_hints']);self.assertFalse(result['audio_analyzed']);self.assertIsNone(result['ai_estimate'])
            self.assertEqual(metadata.read_profile(temp,'a')['facts']['artist'],'Artist')
    def test_annotations_are_estimates(self):
        items=ai.annotations({'annotations':[{'id':'a','genres':['Jazz'],'moods':['calm'],'confidence':.7,'energy':'low','evidence':'Tags'},{'id':'outside'}]}, {'a'})
        self.assertEqual(len(items),1);self.assertIn('audio not analyzed',items[0]['basis'])
    def test_groq_catalog_bounds_large_and_unicode_metadata(self):
        tracks=[{'id':str(i),'title':'音楽'*200,'artist':'Artist','duration':100} for i in range(250)]
        profiles={t['id']:{'facts':{'description':'jazz '*10000,'tags':['jazz'*200]*100,'genres_reported':['Jazz']},'genre_hints':['jazz']} for t in tracks}
        catalog=ai.build_catalog(tracks,profiles,'jazz',self.config('groq'))
        self.assertTrue(catalog);self.assertLess(len(catalog),250)
        self.assertLess(len(json.dumps({'request':'jazz','library':catalog},ensure_ascii=False,separators=(',',':')).encode()),8100)
        self.assertEqual(catalog[0]['reported_genres'],['Jazz'])
        _,_,body=ai.request_payload(self.config('groq'),'test-key','prompt')
        self.assertEqual(body['max_tokens'],2000)
    def test_size_rejection_retries_smaller_catalog_once(self):
        config=self.config('groq');ai.SESSION_KEYS[ai.account(config)]='test-key'
        response=MagicMock();response.__enter__.return_value=response
        response.read.return_value=json.dumps({'choices':[{'message':{'content':'{"track_ids":["a"]}'}}]}).encode()
        opener=MagicMock();opener.open.side_effect=[HTTPError(config['endpoint'],413,'too large',{},None),response]
        prompt=json.dumps({'request':'jazz','library':[{'id':'a','description':'long'},{'id':'b'}]})
        with patch.object(ai,'build_opener',return_value=opener):self.assertEqual(ai.call_provider(config,prompt)['track_ids'],['a'])
        retried=json.loads(json.loads(opener.open.call_args.args[0].data)['messages'][1]['content'])
        self.assertEqual(retried['library'],[{'id':'a'}]);self.assertEqual(opener.open.call_count,2)
        opener.open.side_effect=[HTTPError(config['endpoint'],413,'secret provider body',{},None)]*2
        opener.open.reset_mock()
        with patch.object(ai,'build_opener',return_value=opener),self.assertRaisesRegex(ValueError,'request size or token budget'):
            ai.call_provider(config,prompt)
        self.assertEqual(opener.open.call_count,2)
    def test_retry_cannot_choose_song_removed_from_shortlist(self):
        config=self.config('groq');ai.SESSION_KEYS[ai.account(config)]='test-key'
        response=MagicMock();response.__enter__.return_value=response
        response.read.return_value=json.dumps({'choices':[{'message':{'content':'{"track_ids":["b"]}'}}]}).encode()
        opener=MagicMock();opener.open.side_effect=[HTTPError(config['endpoint'],413,'too large',{},None),response]
        with patch.object(ai,'build_opener',return_value=opener),self.assertRaisesRegex(ValueError,'outside'):
            ai.call_provider(config,json.dumps({'library':[{'id':'a'},{'id':'b'}]}))

class PlaylistLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.env=patch.dict(os.environ,{'AURAL_DATA':self.temp.name});self.env.start()
        spec=importlib.util.spec_from_file_location('ai_test_app',Path(__file__).resolve().parents[1]/'app.py');self.app=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.app)
        file=Path(self.temp.name)/'a-audio.info.json';file.write_text(json.dumps({'title':'Jazz fixture','tags':['jazz'],'duration':100}));file.with_name('a-audio.mp3').write_bytes(b'audio')
    def tearDown(self):self.env.stop();self.temp.cleanup();ai.clear_session_keys()
    def test_temporary_rename_save_and_cleanup(self):
        app=self.app;app.TEMP_PLAYLISTS.append({'id':'mix','name':'Temp','color':'#d1f294','tracks':['a-audio'],'temporary':True,'ai':True})
        app.edit_playlist({'action':'update','id':'mix','name':'My jazz','color':'#c7b5ff'});self.assertEqual(json.loads(app.PLAYLISTS.read_text()),[])
        self.assertEqual(app.playlists()[0]['name'],'My jazz');app.edit_playlist({'action':'save','id':'mix'});self.assertEqual(len(app.TEMP_PLAYLISTS),0)
        app.TEMP_PLAYLISTS.append({'id':'other','name':'Other','color':'#ffffff','tracks':[],'temporary':True});app.clear_temporary();self.assertEqual([p['name'] for p in app.playlists()],['My jazz'])
    def test_generation_preserves_order_and_metadata(self):
        app=self.app;app.AI_JOBS['job']={'status':'generating'}
        result={'name':'Jazz to relax','track_ids':['a-audio'],'reason':'Jazz tags','annotations':[{'id':'a-audio','genres':['jazz'],'moods':['calm'],'confidence':.8}]}
        with patch.object(ai,'call_provider',return_value=result):app.generate_ai_playlist('job','calm jazz','#d1f294',{})
        self.assertEqual(app.AI_JOBS['job']['status'],'complete');self.assertTrue(app.playlists()[0]['temporary']);self.assertFalse(app.PLAYLISTS.exists());self.assertEqual(metadata.read_profile(app.DATA,'a-audio')['ai_estimate']['genres'],['jazz'])
    def test_no_playlist_after_session_closes(self):
        app=self.app;app.AI_JOBS['job']={'status':'generating'};app.clear_temporary()
        with patch.object(ai,'call_provider',return_value={'name':'No','track_ids':['a-audio']}):app.generate_ai_playlist('job','jazz','#d1f294',{})
        self.assertEqual(app.TEMP_PLAYLISTS,[])
    def test_api_key_not_in_settings_file(self):
        with patch.object(ai,'secure_backend',return_value=None):reply=self.app.update_ai_config({'provider':'openai','model':'test-model','key':'test-key','remember':False})
        self.assertTrue(reply['has_key']);self.assertNotIn('test-key',(self.app.DATA/'settings.json').read_text());self.assertNotIn('key',reply)

if __name__=='__main__':unittest.main()
