"""Record an actual SIGINT and paid hosted resume; never prints credentials."""
import json,os,signal,sqlite3,subprocess,sys,threading,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pipeline import hosted as h
ROOT=h.ROOT;folder=ROOT/'evidence/hosted';folder.mkdir(parents=True,exist_ok=True)
def snapshot():
 d=h.c.dbopen(h.STATE/'partial.sqlite');ids=[r[0] for r in d.execute('SELECT id FROM labels WHERE config=? ORDER BY id',(h.LABEL_CONFIG,))];d.close();return {'completed_ids':ids,'label_config':h.LABEL_CONFIG}
def main():
 db=h.initialize('partial')
 if snapshot()['completed_ids']:raise ValueError('Demo requires fresh partial configuration')
 start=time.monotonic();cast=(folder/'resume.cast').open('w');cast.write(json.dumps({'version':2,'width':120,'height':30,'timestamp':int(time.time()),'title':'Actual hosted batch SIGINT and resume; no repeated completed IDs'})+'\n')
 def record(line):
  cast.write(json.dumps([time.monotonic()-start,'o',line+'\r\n'])+'\n');cast.flush();print(line,flush=True)
 def launch(extra):
  args=[sys.executable,'-u',str(ROOT/'pipeline/hosted.py'),'partial','--execute-paid','--spend-cap','4.90',*extra];record('$ python3 pipeline/hosted.py partial --execute-paid --spend-cap 4.90 '+' '.join(extra));p=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,cwd=ROOT)
  t=threading.Thread(target=lambda:[record(line.rstrip()) for line in p.stdout],daemon=True);t.start();return p,t
 first,t=launch([]);deadline=time.monotonic()+600
 while first.poll() is None:
  if len(snapshot()['completed_ids'])>=50:record('Sending SIGINT after committed hosted progress');first.send_signal(signal.SIGINT);break
  if time.monotonic()>deadline:first.terminate();raise RuntimeError('No saved progress before demo timeout')
  time.sleep(.2)
 first.wait(timeout=200);t.join(timeout=3);before=snapshot();h.c.dump(folder/'checkpoint_before.json',before)
 if not before['completed_ids']:raise RuntimeError('No progress saved; do not fabricate resume')
 second,t=launch(['--phase','resume','--stop-after-batches','2']);code=second.wait(timeout=600);t.join(timeout=3)
 if code:raise RuntimeError('Resume failed; inspect credential-safe console')
 after=snapshot();h.c.dump(folder/'checkpoint_after.json',after)
 d=h.c.dbopen(db);new=[json.loads(r[0]) for r in d.execute("SELECT payload FROM calls WHERE role='enrich' AND phase='resume'")];d.close();repeated=set(before['completed_ids'])&{rid for call in new for rid in call['review_ids']}
 assert len(after['completed_ids'])>len(before['completed_ids']) and not repeated
 proof={'actual_signal':'SIGINT','interrupted_process_exit_code':first.returncode,'before':len(before['completed_ids']),'after':len(after['completed_ids']),'resume_attempts':len(new),'repeated_completed_ids':sorted(repeated),'budget':h.budget_status()};h.c.dump(folder/'resume-check.json',proof);record(json.dumps(proof));cast.close()
if __name__=='__main__':main()
