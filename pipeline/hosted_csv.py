"""Arbitrary source CSV entrypoint. Offline profile by default; explicit capped execution."""
import argparse,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pipeline import hosted as h
from pipeline.hosted_finish import finish

def main():
 p=argparse.ArgumentParser();p.add_argument('input',type=Path);p.add_argument('--execute-paid',action='store_true');p.add_argument('--spend-cap',type=float);a=p.parse_args()
 if (h.ROOT/'evals').resolve() in a.input.resolve().parents:raise ValueError('evals/ contains evaluation answers/outputs and must never be used as model input')
 rows=list(h.c.csv_rows(a.input));fields={'review_id','review_text','review_rating','review_likes','app_version','review_timestamp'}
 if not rows or any(set(r)!=fields for r in rows):raise ValueError('Provide exactly the six original source columns, without human answers or additional metadata')
 name='csv-'+h.c.sha(a.input)[:16];db=h.STATE/(name+'.sqlite');report={'mode':'offline_profile','rows':len(rows),'nonempty':sum(bool(r['review_text'].strip()) for r in rows),'input_sha256':h.c.sha(a.input),'label_config':h.LABEL_CONFIG,'database':str(db),'api_calls':0}
 if not a.execute_paid:print(json.dumps(report));return
 if a.spend_cap is None or not 0<a.spend_cap<=4.90:p.error('Paid execution requires positive --spend-cap <=4.90')
 if report['nonempty']>100:
  from cost.hosted_calculator import calculate
  projection=calculate(report['nonempty'])
  if projection['label_config']!=h.LABEL_CONFIG or projection['conservative_100000_total_usd']>=4:raise RuntimeError('Projection gate: matching profile and under-$4 projection required')
 h.CAP=round(a.spend_cap*1e6);h.credentials();h.activate();h.c.ingest(a.input,db);h.acquire();d=h.c.dbopen(db);run=name+'-'+str(__import__('uuid').uuid4())
 try:
  h.recover(d);pending=[];hashes=set()
  def flush():
   if pending:h.save_results(d,pending,h.request(d,pending,run));pending.clear();hashes.clear()
  for row in d.execute("SELECT * FROM sources WHERE status!='quarantined' ORDER BY ordinal").fetchall():
   if d.execute('SELECT 1 FROM labels WHERE id=? AND config=?',(row['id'],h.LABEL_CONFIG)).fetchone():continue
   if row['text_hash'] in hashes:flush()
   cached=d.execute('SELECT * FROM cache WHERE text_hash=? AND config=?',(row['text_hash'],h.LABEL_CONFIG)).fetchone()
   if cached:
    with d:d.execute('INSERT INTO labels VALUES(?,?,?,?)',(row['id'],h.LABEL_CONFIG,cached['result'],cached['source_id']))
   else:pending.append(row);hashes.add(row['text_hash'])
   if len(pending)==50 or sum(len(r['text'].encode()) for r in pending)>60000:flush()
  flush();h.aggregate(d)
 finally:d.close();h.release()
 finish(name);out=h.ROOT/'evidence/hosted'/name;h.c.export(db,out,a.input);h.c.dump(out/'ingestion.json',h.c.profile(a.input));print(json.dumps({'status':'complete','export':str(out),'budget':h.budget_status()}))
if __name__=='__main__':main()
