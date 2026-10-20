"""Optional model issue naming; memberships/arithmetic stay code. Explicit paid flag only."""
import argparse,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pipeline import hosted as h
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--execute-paid',action='store_true');p.add_argument('--spend-cap',type=float);a=p.parse_args()
 if not a.execute_paid:print(json.dumps({'mode':'offline','role':'group','operation':'name eight code-computed issues only','estimated_additional_cost_usd_less_than':.001,'paid_execution_requires_explicit_flag':True}));raise SystemExit(0)
 if a.spend_cap is None or not 0<a.spend_cap<=4.90:p.error('Positive cap <=4.90 required')
 h.CAP=round(a.spend_cap*1e6);h.acquire();d=h.c.dbopen(h.STATE/'partial.sqlite')
 try:
  packs=h.aggregate(d);extra={'issues':packs};key='issue-names-v1-'+hashlib.sha256(json.dumps({'config':h.LABEL_CONFIG,'input':extra},sort_keys=True).encode()).hexdigest();old=d.execute('SELECT value FROM artifacts WHERE key=?',(key,)).fetchone()
  if old:result=json.loads(old[0])
  else:
   result=h.request(d,[],'issue-names-once',role='group',extra=extra,artifact_key=key)
   with d:d.execute('INSERT INTO artifacts VALUES(?,?)',(key,json.dumps(result)))
  h.c.dump(h.ROOT/'evidence/hosted/partial-group-titles.json',result);print(json.dumps(result))
 finally:d.close();h.release()
