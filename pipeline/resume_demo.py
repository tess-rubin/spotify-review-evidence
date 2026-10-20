"""Record a real SIGINT and resume as an asciicast v2 terminal recording."""
import json,sqlite3,subprocess,time,signal,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pipeline.core import LABEL_CONFIG,dump
ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
 db=ROOT/'data/checkpoint500.sqlite';src=sqlite3.connect(ROOT/'data/pilot.sqlite');dest=sqlite3.connect(db);src.backup(dest);src.close();dest.close()
 subprocess.run([sys.executable,'pipeline/core.py','ingest','supplied/checkpoint_500.csv','--db',str(db)],check=True,cwd=ROOT)
 start=time.monotonic();record=open(ROOT/'evidence/resume.cast','w');record.write(json.dumps({'version':2,'width':110,'height':30,'timestamp':int(time.time()),'title':'Spotify pipeline: real interruption and saved-state resume'})+'\n')
 def event(s):record.write(json.dumps([time.monotonic()-start,'o',s+'\r\n'])+'\n');record.flush()
 command=[sys.executable,'-u','pipeline/core.py','execute-local','supplied/checkpoint_500.csv','--db',str(db),'--spend-cap','4.90','--name','checkpoint-interrupted']
 event('$ '+' '.join(command));p=subprocess.Popen(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);succeeded=0
 for line in p.stdout:
  event(line.rstrip());
  try:v=json.loads(line)
  except ValueError:continue
  if v.get('role')=='enrich' and v.get('outcome')=='succeeded':succeeded+=1
  if succeeded>=20:
   time.sleep(.15);p.send_signal(signal.SIGINT);event('^C [real SIGINT sent after saved progress]');break
 for line in p.stdout:event(line.rstrip())
 p.wait()
 def snap(name):
  d=sqlite3.connect(db);ids=[r[0] for r in d.execute('SELECT id FROM labels WHERE config=? ORDER BY id',(LABEL_CONFIG,))];calls=[json.loads(r[0]) for r in d.execute('SELECT payload FROM calls')];d.close();dump(ROOT/'evidence'/name,{'completed_ids':ids,'enrichment_request_ids':[c['request_id'] for c in calls if c['role']=='enrich'],'label_config':LABEL_CONFIG});return set(ids),calls
 before,calls_before=snap('checkpoint_before.json');event('Saved before snapshot: '+str(len(before))+' completed IDs')
 command=[sys.executable,'-u','pipeline/core.py','execute-local','supplied/checkpoint_500.csv','--db',str(db),'--spend-cap','4.90','--phase','resume','--stop-after','20','--name','checkpoint-resumed']
 event('$ '+' '.join(command));p=subprocess.Popen(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 for line in p.stdout:event(line.rstrip())
 rc=p.wait();after,calls_after=snap('checkpoint_after.json');prior={c['request_id'] for c in calls_before};new=[c for c in calls_after if c['request_id'] not in prior and c['role']=='enrich'];repeated=sorted({rid for c in new for rid in c['review_ids']}&before)
 result={'before_completed':len(before),'after_completed':len(after),'new_enrichment_attempts':len(new),'already_completed_ids_resent':repeated,'actual_sigint':True,'resume_exit_code':rc};dump(ROOT/'evidence/resume-check.json',result);event(json.dumps(result));record.close();assert not repeated and len(after)>len(before)
