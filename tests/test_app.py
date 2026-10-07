import os, pathlib, tempfile, importlib.util, unittest, io, json
from types import SimpleNamespace
from unittest.mock import patch
import sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
scratch=tempfile.TemporaryDirectory();os.environ['AURAL_DATA']=scratch.name
spec=importlib.util.spec_from_file_location('aural',str(pathlib.Path(__file__).resolve().parents[1]/'app.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Tests(unittest.TestCase):
 def setUp(self):
  for p in m.DATA.glob('*'):p.unlink()
  m.jobs.clear()
 def track(self):
  stem='dQw4w9WgXcQ-audio';(m.DATA/(stem+'.info.json')).write_text(json.dumps({'title':'Test'}));(m.DATA/(stem+'.mp3')).write_bytes(b'music');return stem
 def post(self,path,body):
  h=object.__new__(m.Handler);raw=json.dumps(body).encode();h.headers={'Content-Length':str(len(raw)),'Origin':'http://127.0.0.1:12345'};h.server=SimpleNamespace(server_port=12345);h.path=path;h.rfile=io.BytesIO(raw);result=[];h.reply=lambda value,status=200:result.append((status,value));h.do_POST();return result[0]
 def test_playlist_lifecycle(self):
  stem=self.track();status,items=self.post('/api/playlists',{'name':'Hard metal','color':'#a064d1'});self.assertEqual(status,200);pid=items[0]['id']
  for _ in range(2):self.post('/api/playlists',{'action':'add','id':pid,'track':stem})
  self.assertEqual(m.playlists()[0]['tracks'],[stem]);self.post('/api/playlists',{'action':'update','id':pid,'name':'Pop','color':'#ff6688'});self.assertEqual(m.playlists()[0]['name'],'Pop')
  status,_=self.post('/api/remove',{'id':stem});self.assertEqual(status,200);self.assertEqual(m.library(),[]);self.assertEqual(m.playlists()[0]['tracks'],[])
 def test_duplicate_saved_and_inflight(self):
  self.track();body={'url':'https://youtu.be/dQw4w9WgXcQ?t=2','kind':'audio'};self.assertEqual(self.post('/api/download',body)[0],400)
  for p in m.DATA.glob('*'):p.unlink()
  with patch.object(m.threading,'Thread') as thread:
   self.assertEqual(self.post('/api/download',body)[0],202);self.assertEqual(self.post('/api/download',dict(body,url='https://www.youtube.com/shorts/dQw4w9WgXcQ'))[0],400);self.assertEqual(thread.call_count,1)
   self.assertEqual(self.post('/api/download',dict(body,kind='video'))[0],400)
 def test_invalid_operations(self):
  self.assertEqual(self.post('/api/remove',{'id':'../anything'})[0],400)
  self.assertEqual(self.post('/api/playlists',{'name':'X','color':'bad'})[0],400)
  self.assertEqual(self.post('/api/download',{'url':'https://evil.test/watch?v=dQw4w9WgXcQ'})[0],400)
 def test_delete_keeps_other_format(self):
  stem=self.track();other=m.DATA/'dQw4w9WgXcQ-video.mp4';other.write_bytes(b'video');m.delete_track(stem);self.assertTrue(other.exists())
class AudioTests(Tests):
 def test_history_and_retries(self):
  import datetime
  track=self.track();base={'track':track,'session':'test-session-one','seconds':10,'day':datetime.datetime.now(datetime.timezone.utc).date().isoformat()}
  for i in range(1,4):self.assertEqual(self.post('/api/listen',dict(base,sequence=i))[0],200)
  self.post('/api/listen',dict(base,sequence=3))
  stats=m.insights();self.assertEqual(stats['plays'],1);self.assertEqual(stats['seconds'],30);self.assertEqual(stats['unique_tracks'],1)
  self.assertEqual(self.post('/api/listen',dict(base,sequence=4,seconds=500))[0],400)
 def test_preferences(self):
  self.post('/api/settings',{'palette':'ocean','layout':'compact','adblock':False})
  value=m.read_settings();self.assertEqual(value['palette'],'ocean');self.assertFalse(value['adblock']);self.assertEqual(value['layout'],'compact')
  self.assertEqual(self.post('/api/settings',{'layout':'invalid'})[0],400)
 def test_old_video_hidden(self):
  (m.DATA/'old-video.info.json').write_text(json.dumps({'title':'Old video'}));(m.DATA/'old-video.mp4').write_bytes(b'video');self.assertEqual(m.library(),[])
if __name__=='__main__':unittest.main()

