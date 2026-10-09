"""Deterministic whole-library filters. Confirmed labels override automatic evidence."""
import re
from song_metadata import GENRES

LANGUAGES={'english':('en','eng'),'malayalam':('ml','mal','മലയാളം'),'hindi':('hi','hin'),'tamil':('ta','tam'),'telugu':('te','tel'),'kannada':('kn','kan'),'bengali':('bn','ben'),'marathi':('mr','mar'),'punjabi':('pa','pan'),'urdu':('ur','urd'),'arabic':('ar','ara'),'spanish':('es','spa'),'portuguese':('pt','por'),'french':('fr','fra','fre'),'german':('de','deu','ger'),'italian':('it','ita'),'russian':('ru','rus'),'korean':('ko','kor'),'japanese':('ja','jpn'),'instrumental':('no vocals',)}

def normalize(value):return re.sub(r'\s+',' ',str(value).strip().casefold())
def language(value):
    value=normalize(value)
    for name,aliases in LANGUAGES.items():
        if value==name or value in aliases:return name
    if re.fullmatch(r'[a-z]{2,3}-[a-z]{2}',value):return language(value.split('-')[0])
    return value

def genre_match(requested,label):
    requested=normalize(requested);label=normalize(label)
    aliases={'hip-hop':'hip hop','rnb':'r&b','rhythm and blues':'r&b'}
    requested=aliases.get(requested,requested);label=aliases.get(label,label)
    if requested==label:return True
    # Parent styles match substyles, e.g. Rock -> Rock / Hard Rock or Hard Rock.
    parts=[normalize(x) for x in label.split(' / ')]
    if requested in parts:return True
    return bool(re.search(r'(?<!\w)'+re.escape(requested)+r'(?!\w)',parts[-1]))

def simple_request(prompt):
    text=normalize(prompt);criteria={}
    for name in sorted(LANGUAGES,key=len,reverse=True):
        if re.search(r'(?<!\w)'+re.escape(name)+r'(?!\w)',text):
            if 'language' in criteria:return None
            criteria['language']=name;text=re.sub(r'(?<!\w)'+re.escape(name)+r'(?!\w)',' ',text)
    for name in sorted(set(GENRES),key=len,reverse=True):
        if re.search(r'(?<!\w)'+re.escape(name)+r'(?!\w)',text):
            if 'genre' in criteria:return None
            criteria['genre']=name;text=re.sub(r'(?<!\w)'+re.escape(name)+r'(?!\w)',' ',text)
    fillers={'i','want','need','give','me','a','an','the','all','only','songs','song','music','tracks','track','playlist','please','make','create','with','of','just','some','for','can','you','get','in','and','hits','hit','listen','to','wanna','would','like','build','include','find','select','add','containing','consisting','ai','new','play','strictly','exclusively'}
    if not criteria or any(word not in fillers for word in re.findall(r'\w+',text)):return None
    return criteria

def criteria(body):
    genre=body.get('genre','');lang=body.get('language','')
    if not isinstance(genre,str) or not isinstance(lang,str) or len(genre)>40 or len(lang)>40:raise ValueError('Choose a genre or language label of at most 40 characters')
    if 'confirmed_only' in body and not isinstance(body['confirmed_only'],bool):raise ValueError('Confirmed labels only must be on or off')
    result={'genre':normalize(genre),'language':language(lang),'confirmed_only':body.get('confirmed_only') is True}
    if not result['genre'] and not result['language']:raise ValueError('Choose a genre or language to filter')
    return result

def evidence(profile,field,requested,confirmed_only):
    user=profile.get('user_labels',{});labels=user.get('genres' if field=='genre' else 'languages',[])
    match=genre_match if field=='genre' else lambda request,label:language(request)==language(label)
    if labels:return any(match(requested,label) for label in labels),'confirmed'
    if confirmed_only:return False,'unknown'
    if field=='language':
        value=profile.get('facts',{}).get('language')
        return (match(requested,value),'reported') if value else (False,'unknown')
    identity=profile.get('identification',{})
    labels=identity.get('genres',[]) if identity.get('status')=='matched' else []
    labels=labels or profile.get('facts',{}).get('genres_reported',[])
    if labels:return any(match(requested,label) for label in labels),'reported'
    predictions=profile.get('audio_analysis',{}).get('genres',[])
    if predictions:
        return any(g.get('score',0)>=.25 and match(requested,g.get('label','')) for g in predictions),'estimated'
    return False,'unknown'

def select(tracks,profiles,filters):
    matches=[];unknown=[];counts={'confirmed':0,'reported':0,'estimated':0}
    for track in tracks:
        checks=[evidence(profiles[track['id']],field,requested,filters['confirmed_only']) for field,requested in filters.items() if field in ('genre','language') and requested]
        if all(result for result,_ in checks):
            level='estimated' if any(level=='estimated' for _,level in checks) else 'reported' if any(level=='reported' for _,level in checks) else 'confirmed'
            counts[level]+=1;matches.append(track['id'])
        elif any(level=='unknown' for _,level in checks):unknown.append(track['id'])
    return {'tracks':matches,'unknown_ids':unknown,'counts':counts,'library_count':len(tracks)}

def name(filters):
    return ' · '.join(value.title() for field,value in filters.items() if field in ('genre','language') and value)[:60]
