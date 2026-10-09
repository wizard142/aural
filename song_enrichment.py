"""One background worker prevents inference from blocking playback or UI requests."""
import queue
import threading
import uuid
from datetime import datetime, timezone
import audio_analysis
import song_identification
from song_metadata import read_profile,save_profile

class Enricher:
    def __init__(self,data,lock,library,settings):
        self.data=data;self.lock=lock;self.library=library;self.settings=settings
        self.queue=queue.Queue();self.jobs={};self.pending=set()
        threading.Thread(target=self.run,daemon=True,name='song-profiles').start()
    def submit(self,tracks,audio=True,identify=False,force=False):
        job_id=uuid.uuid4().hex;queued=[]
        with self.lock:
            for track in tracks:
                profile=read_profile(self.data,track['id'])
                use_audio=audio and (force or profile.get('audio_analysis',{}).get('version')!=audio_analysis.VERSION)
                use_id=identify and (force or profile.get('identification',{}).get('status')!='matched')
                if not (use_audio or use_id) or track['id'] in self.pending:continue
                self.pending.add(track['id']);queued.append((track,use_audio,use_id))
            self.jobs[job_id]={'id':job_id,'status':'queued' if queued else 'complete','total':len(queued),'done':0,'failed':0,'detail':'Song profiles are up to date.' if not queued else 'Queued','errors':[]}
            self.jobs={k:v for k,v in list(self.jobs.items())[-30:]}
        self.queue.put((job_id,queued));return job_id
    def run(self):
        while True:
            job_id,tracks=self.queue.get()
            with self.lock:self.jobs[job_id]['status']='processing' if tracks else 'complete'
            for track,audio,identify in tracks:
                updates={};errors=[]
                def progress(message):
                    with self.lock:self.jobs[job_id]['detail']=message+' '+track['title'][:120]
                try:
                    with self.lock:
                        if track['id'] not in {t['id'] for t in self.library()}:continue
                        profile=read_profile(self.data,track['id'])
                    media=self.data/track['file']
                    if audio:
                        try:
                            updates['audio_analysis']=audio_analysis.analyze(media,track['duration'],self.data,progress)
                            updates['audio_analyzed']=True
                        except Exception as e:errors.append(str(e) if isinstance(e,(ValueError,FileNotFoundError)) else 'Audio analysis failed. Check model installation and audio dependencies.')
                    if identify:
                        try:
                            progress('Identifying recording…')
                            fp=profile.get('fingerprint') or song_identification.fingerprint(media)
                            updates['fingerprint']=fp
                            fp,result=song_identification.identify(media,fp)
                            updates.update(fingerprint=fp,identification=result)
                        except Exception as e:errors.append(str(e) if isinstance(e,(ValueError,FileNotFoundError)) else 'Recording identification failed.')
                    with self.lock:
                        # Merge the latest profile so concurrent corrections cannot be overwritten.
                        if track['id'] in {t['id'] for t in self.library()}:
                            latest=read_profile(self.data,track['id']);latest.update(updates)
                            latest['profile_errors']=errors;latest['analyzed_at']=datetime.now(timezone.utc).isoformat()
                            save_profile(self.data,track['id'],latest)
                except Exception:
                    errors.append('Could not update this song profile. Try again after downloads finish.')
                finally:
                    with self.lock:
                        self.pending.discard(track['id']);job=self.jobs[job_id];job['done']+=1
                        if errors:job['failed']+=1;job['errors'].extend(errors[:2]);job['errors']=job['errors'][:10]
            with self.lock:
                job=self.jobs[job_id];job['status']='complete' if not job['failed'] else 'partial'
                job['detail']=f"Processed {job['done']} of {job['total']} songs."+(f" {job['failed']} need attention." if job['failed'] else '')
            self.queue.task_done()
