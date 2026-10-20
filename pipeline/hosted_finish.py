"""Code-only issue membership/ranking, blind verification and bounded hosted memo.
Never reads human answers. Uses the same global API ledger as classification.
"""
import argparse,hashlib,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pipeline import hosted as h
c=h.c;ROOT=h.ROOT

def finish(scope):
 h.activate();h.credentials();h.acquire();started=time.monotonic();d=c.dbopen(h.STATE/(scope+'.sqlite'));run='finish-'+scope+'-'+str(__import__('uuid').uuid4());new={'verify':0,'memo':0}
 try:
  packs=h.aggregate(d)
  rows=h.selected_rows(d,scope); completed=[r for r in rows if d.execute('SELECT 1 FROM labels WHERE id=? AND config=?',(r['id'],h.LABEL_CONFIG)).fetchone()]
  sample=sorted(completed,key=lambda r:hashlib.sha256(('hosted-blind-v1'+r['id']).encode()).hexdigest())[:10]
  for role,payload,selected in [('verify',None,sample),('memo',{'issues':packs},[])]:
   if role=='memo' and not packs:continue
   identity={'role':role,'role_version':'hosted-finish-v1','prompt':h.MEMO_PROMPT if role=='memo' else 'Independently classify, blind to any prior predictions. '+h.PROMPT,'label_config':h.LABEL_CONFIG,'rows':[{k:r[k] for k in ('id','text_hash')} for r in selected],'payload':payload}
   key='hosted-finish-'+hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest();old=d.execute('SELECT value FROM artifacts WHERE key=?',(key,)).fetchone()
   if old:result=json.loads(old[0])
   else:
    saved=[json.loads(r[0]) for r in d.execute('SELECT payload FROM calls WHERE role=? AND outcome=?',(role,'succeeded'))]
    recovered=next((log['validated_result'] for log in saved if (log.get('artifact_key')==key or (log.get('input')==(payload if payload is not None else {'reviews':{'r'+str(i):r['text'] for i,r in enumerate(selected)}}) and log.get('review_ids')==[r['id'] for r in selected] and log.get('request_body',{}).get('messages',[{}])[0].get('content')==identity['prompt'])) and log.get('label_config')==h.LABEL_CONFIG and log.get('settings')==h.CONFIG),None)
    if recovered is not None:
     result=recovered
     if role=='memo':h.validate_memo(result,payload)
     else:c.validate({'results':[dict(value,review_id=rid) for rid,value in result.items()]},selected)
    else:result=h.request(d,selected,run,role=role,extra=payload,artifact_key=key);new[role]+=1
    with d:d.execute('INSERT INTO artifacts VALUES(?,?)',(key,json.dumps(result,ensure_ascii=False)))
   c.dump(ROOT/'evidence/hosted'/(scope+'-'+role+'.json'),result)
   if role=='verify':
    disagreements=[]
    for rid,pred in result.items():
     original=json.loads(d.execute('SELECT result FROM labels WHERE id=? AND config=?',(rid,h.LABEL_CONFIG)).fetchone()[0]);fields=[f for f in ('topic','intent','severity','sentiment','needs_review') if original[f]!=pred[f]]
     if fields:disagreements.append({'review_id':rid,'fields':fields,'original':original,'blind':pred})
    c.dump(ROOT/'evidence/hosted'/(scope+'-verification-comparison.json'),{'sample_size':len(result),'disagreements':disagreements,'not_accuracy':'Independent same-model agreement is a consistency check, not ground truth.'})
  calls=[json.loads(r[0]) for r in d.execute('SELECT payload FROM calls WHERE run_id=?',(run,))]
  report={'run_id':run,'scope':scope,'label_config':h.LABEL_CONFIG,'new_calls':new,'calls_attempted':len(calls),'seconds':time.monotonic()-started,'budget':h.budget_status(),'aggregate_count':len(packs)};c.dump(ROOT/'evidence/hosted'/(scope+'-finish-latest.json'),report);print(json.dumps(report),flush=True)
  return report
 finally:d.close();h.release()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('scope',choices=['pilot','partial']);p.add_argument('--execute-paid',action='store_true');p.add_argument('--spend-cap',type=float,required=True);a=p.parse_args()
 if not a.execute_paid or not 0<a.spend_cap<=4.9:p.error('Explicit paid execution cap required')
 h.CAP=round(a.spend_cap*1e6)
 try:finish(a.scope)
 except RuntimeError as e:print(str(e),file=sys.stderr);sys.exit(2)
