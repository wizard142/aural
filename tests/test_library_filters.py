import unittest
from unittest.mock import patch
import importlib.util
import tempfile
from pathlib import Path
import json,os
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import library_filters as filters
import ai_playlists as ai
import song_metadata

class WholeLibraryTests(unittest.TestCase):
    def test_all_matches_beyond_ai_limits_and_shortlists(self):
        tracks=[{'id':str(i)} for i in range(400)]
        profiles={t['id']:{'user_labels':{'genres':['hard rock']}} for t in tracks}
        result=filters.select(tracks,profiles,filters.criteria({'genre':'rock','confirmed_only':True}))
        self.assertEqual(result['tracks'],[str(i) for i in range(400)])
        self.assertEqual(result['counts']['confirmed'],400)
    def test_sweet_child_rock_prediction_and_corrections(self):
        tracks=[{'id':'sweet'},{'id':'jazz'}]
        profiles={'sweet':{'audio_analysis':{'genres':[{'label':'Rock / Hard Rock','score':.617}]}},'jazz':{'user_labels':{'genres':['jazz']},'audio_analysis':{'genres':[{'label':'Rock / Hard Rock','score':.9}]}}}
        result=filters.select(tracks,profiles,filters.criteria({'genre':'rock'}))
        self.assertEqual(result['tracks'],['sweet']);self.assertEqual(result['counts']['estimated'],1)
        confirmed=filters.select(tracks,profiles,filters.criteria({'genre':'rock','confirmed_only':True}))
        self.assertEqual(confirmed['tracks'],[]);self.assertEqual(confirmed['unknown_ids'],['sweet'])
    def test_all_five_malayalam_tracks_and_multilingual_aliases(self):
        tracks=[{'id':str(i)} for i in range(7)]
        profiles={str(i):{'user_labels':{'languages':['malayalam','english'] if i==4 else ['Malayalam']}} for i in range(5)}
        profiles['5']={'user_labels':{'languages':['english']},'facts':{'language':'ml'}}
        profiles['6']={'facts':{'language':''}}
        result=filters.select(tracks,profiles,filters.criteria({'language':'mal','confirmed_only':True}))
        self.assertEqual(result['tracks'],[str(i) for i in range(5)]);self.assertEqual(result['unknown_ids'],['6'])
        self.assertEqual(result['counts']['confirmed'],5)
    def test_source_language_and_genre_and_language_intersection(self):
        tracks=[{'id':'a'},{'id':'b'}]
        profiles={'a':{'facts':{'language':'en-US','genres_reported':['hard rock']}},'b':{'facts':{'language':'ml','genres_reported':['rock']}}}
        result=filters.select(tracks,profiles,filters.criteria({'genre':'rock','language':'english'}))
        self.assertEqual(result['tracks'],['a']);self.assertEqual(result['counts']['reported'],1)
    def test_simple_prompts_route_locally_but_complex_prompts_do_not(self):
        self.assertEqual(filters.simple_request('rock songs only'),{'genre':'rock'})
        self.assertEqual(filters.simple_request('give me all Malayalam songs'),{'language':'malayalam'})
        self.assertEqual(filters.simple_request('only hard rock songs in English'),{'language':'english','genre':'hard rock'})
        for text in ('rock then jazz','sad rock songs','not rock','songs by Queen','rock songs under 3 minutes'):
            self.assertIsNone(filters.simple_request(text))
    def test_language_is_sent_to_ai_for_complex_requests(self):
        tracks=[{'id':'a','title':'Song','artist':'Singer','duration':100}]
        profiles={'a':{'facts':{'language':'ml'},'user_labels':{'languages':['malayalam']}}}
        catalog=ai.build_catalog(tracks,profiles,'sad Malayalam for a rainy day')
        self.assertEqual(catalog[0]['language'],'ml');self.assertEqual(catalog[0]['user_labels']['languages'],['malayalam'])

class LocalGenerationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.env=patch.dict(os.environ,{'AURAL_DATA':self.temp.name});self.env.start()
        spec=importlib.util.spec_from_file_location('filter_test_app',Path(__file__).resolve().parents[1]/'app.py');self.app=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.app)
        for i in range(5):
            tid=f'{i}-audio';root=Path(self.temp.name)
            (root/(tid+'.info.json')).write_text(json.dumps({'title':f'Track {i}','duration':100}));(root/(tid+'.mp3')).write_bytes(b'fixture')
            song_metadata.update_labels(root,tid,{'genres':['rock'],'languages':['malayalam']})
    def tearDown(self):self.env.stop();self.temp.cleanup()
    def test_generation_uses_every_match_without_provider(self):
        app=self.app;app.AI_JOBS['job']={'status':'generating'}
        with patch.object(ai,'call_provider') as call:
            app.generate_ai_playlist('job','Malayalam songs','#d1f294',{},filters.criteria({'language':'malayalam','confirmed_only':True}))
            call.assert_not_called()
        self.assertEqual(app.AI_JOBS['job']['status'],'complete');self.assertEqual(len(app.playlists()[0]['tracks']),5)
        self.assertFalse(app.playlists()[0]['ai']);self.assertEqual(app.playlists()[0]['filter_report']['counts']['confirmed'],5)
    def test_simple_request_needs_no_key_or_consent(self):
        with patch.object(ai,'get_key',return_value=''),patch.object(ai,'call_provider') as call:
            job=self.app.start_ai_playlist({'prompt':'rock songs only','color':'#d1f294'})
            import time
            for _ in range(50):
                if self.app.AI_JOBS[job['id']]['status']!='generating':break
                time.sleep(.01)
            self.assertEqual(self.app.AI_JOBS[job['id']]['status'],'complete');call.assert_not_called()

if __name__=='__main__':unittest.main()
