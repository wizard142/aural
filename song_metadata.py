"""Private local song profiles. Source facts and estimates remain separate."""
import json
import re
from pathlib import Path
from datetime import datetime, timezone

GENRES=('pop','rock','metal','heavy metal','hard rock','hip hop','hip-hop','rap','jazz','blues','classical','country','folk','electronic','ambient','house','techno','trance','dubstep','r&b','soul','funk','reggae','punk','indie','k-pop','j-pop','lo-fi','latin','disco','gospel')

def profile_path(data, track_id): return Path(data)/(track_id+'.song.json')

def capture_profile(data, track_id):
    info_path=Path(data)/(track_id+'.info.json')
    info=json.loads(info_path.read_text(encoding='utf-8'))
    def text(key,limit=500):return str(info.get(key) or '')[:limit]
    def strings(key):
        value=info.get(key) or []
        if isinstance(value,str):value=[value]
        return [str(x)[:100] for x in value if isinstance(x,(str,int))][:30]
    facts={'track':text('track') or text('title'),'artist':text('artist') or ', '.join(strings('artists')) or text('creator') or text('uploader'),'artists':strings('artists'),'album':text('album'),'release_year':info.get('release_year'),'duration':info.get('duration'),'genres_reported':strings('genres') or strings('genre'),'tags':strings('tags'),'categories':strings('categories'),'description':text('description',1800),'language':text('language',50),'channel':text('channel'),'source_url':text('webpage_url',500),'license':text('license')}
    evidence=' '.join(facts['tags']+facts['categories']+[facts['description']]).lower()
    hints=[genre for genre in GENRES if re.search(r'(?<!\w)'+re.escape(genre)+r'(?!\w)',evidence)]
    result={'version':1,'id':track_id,'source':'download metadata','captured_at':datetime.now(timezone.utc).isoformat(),'facts':facts,'genre_hints':hints,'hint_basis':'tags/categories/description keywords; not verified','audio_analyzed':False,'ai_estimate':None}
    path=profile_path(data,track_id)
    if path.exists():
        old=json.loads(path.read_text(encoding='utf-8'));result['ai_estimate']=old.get('ai_estimate')
    save_profile(data,track_id,result);return result

def save_profile(data,track_id,result):
    path=profile_path(data,track_id);temp=path.with_suffix('.tmp');temp.write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8');temp.replace(path)

def read_profile(data,track_id):
    path=profile_path(data,track_id)
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else capture_profile(data,track_id)
