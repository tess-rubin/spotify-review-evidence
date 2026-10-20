"""Offline checker against a consistent snapshot while the hosted run continues."""
import json,shutil,sqlite3,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pipeline import hosted as h
ROOT=h.ROOT
if __name__=='__main__':
 h.activate();source=sqlite3.connect('file:'+str(h.STATE/'partial.sqlite')+'?mode=ro',uri=True);target=sqlite3.connect(h.STATE/'preflight.sqlite');source.backup(target);source.close();target.close();d=h.c.dbopen(h.STATE/'preflight.sqlite');h.aggregate(d);d.close();out=ROOT/'evidence/hosted/preflight-grading';h.c.export(h.STATE/'preflight.sqlite',out,ROOT/'supplied/spotify_reviews_18months.csv')
 for fn in ('checkpoint_before.json','checkpoint_after.json'):shutil.copyfile(ROOT/'evidence/hosted'/fn,out/fn)
 shutil.copyfile(ROOT/'grading/ingestion.json',out/'ingestion.json')
 calls=[json.loads(line) for line in (out/'calls.jsonl').read_text().splitlines() if line.strip()]
 for call in calls:
  if call['outcome'] in ('interrupted','in_flight'):call['original_outcome']=call['outcome'];call['outcome']='failed';call['usage_status']='unavailable_at_snapshot; reservation retained'
 (out/'calls.jsonl').write_text(''.join(json.dumps(c,ensure_ascii=False)+'\n' for c in calls))
 result=subprocess.run([sys.executable,str(ROOT/'supplied/check_submission.py'),'check','--reference',str(ROOT/'local-reference.json'),'--submission',str(out),'--out',str(ROOT/'evidence/hosted/preflight-check.json')],capture_output=True,text=True);(ROOT/'evidence/hosted/preflight-check-console.log').write_text(result.stdout+result.stderr)
 p=json.loads((ROOT/'evidence/hosted/preflight-check.json').read_text());print(json.dumps({'status':p['status'],'coverage':p['coverage'],'issues':p['issue_counts']}))
