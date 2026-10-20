"""Build an offline bounded seed from final hosted partial aggregates, not model calls."""
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pipeline import hosted as h
ROOT=h.ROOT

def build():
 d=h.c.dbopen(h.STATE/'partial.sqlite');completed=d.execute('SELECT count(*) FROM labels WHERE config=?',(h.LABEL_CONFIG,)).fetchone()[0]
 if completed<100000:raise RuntimeError('Final hosted dashboard requires >=100000 completed rows')
 packs=[json.loads(r[0]) for r in d.execute('SELECT payload FROM aggregates WHERE config=?',(h.LABEL_CONFIG,))];chosen=set()
 names_path=ROOT/'evidence/hosted/partial-group-titles.json'
 if names_path.exists():
  names={r['issue_id']:r['title'] for r in json.loads(names_path.read_text())['titles']}
  for pack in packs:pack['title']=names[pack['issue_id']]
 for p in packs:chosen.update(e['review_id'] for e in p['evidence'])
 # At most 400 reviews, including every cited source and a deterministic sample.
 candidates=d.execute('SELECT s.id FROM sources s JOIN labels l ON s.id=l.id WHERE l.config=? ORDER BY s.text_hash,s.ordinal LIMIT 400',(h.LABEL_CONFIG,))
 for r in candidates:
  if len(chosen)>=400:break
  chosen.add(r['id'])
 rows=[]
 for rid in sorted(chosen):
  r=d.execute('SELECT s.*,l.result,l.cache_source_id FROM sources s JOIN labels l ON s.id=l.id WHERE s.id=? AND l.config=?',(rid,h.LABEL_CONFIG)).fetchone();v={'scope':'partial','review_id':rid,'review_text':r['text'],'source_sha256':r['row_hash'],'status':'completed','label_config':h.LABEL_CONFIG,**json.loads(r['result'])};rows.append({'kind':'review','value':v})
 for p in packs:rows.append({'kind':'aggregate','value':{'scope':'partial',**p}})
 for rec in json.loads((ROOT/'evidence/hosted/partial-memo.json').read_text())['recommendations']:rows.append({'kind':'recommendation','value':{'scope':'partial',**rec}})
 calls=[json.loads(r[0]) for r in d.execute('SELECT payload FROM calls')]
 for call in calls[-100:]:rows.append({'kind':'call','value':{k:call.get(k) for k in ('request_id','run_id','role','review_ids','model','label_config','outcome','input_tokens','output_tokens','api_cost_usd','duration_seconds')}})
 cold=json.loads((ROOT/'cost/hosted-measured.json').read_text());budget=h.budget_status();summary={'status':f'PARTIAL RUN: {completed:,} hosted classifications out of 660,609 nonempty reviews; all 660,622 rows ingested. Rankings use only hosted classifications. The 66,577 historical Gemma rows are separate. Hosted evidence is a sample; complete classified records are in grading/.','full_source_rows':660622,'full_completed':completed,'empty_quarantines':13,'hosted_evidence_rows':len(chosen),'historical_gemma_rows':66577,'api_cost_usd':budget['spent_usd'],'unknown_reserved_usd':budget['reserved_or_unknown_usd'],'hard_cap_usd':4.90,'cold_seconds':cold['cold_pipeline_seconds'],'warm_enrichment_calls':0,'calls':len(calls),'analysis_scope':f'{completed:,} hosted partial-run classifications; code grouping/ranking; no confirmed churn or revenue inference','hosted_review_scope':f'{len(chosen)} inspectable saved source reviews; full classified records remain in local grading export','model':h.CONFIG['model'],'label_config':h.LABEL_CONFIG}
 rows.append({'kind':'snapshot','value':summary});seed=json.dumps(rows,ensure_ascii=False,separators=(',',':'));seedid=hashlib.sha256(seed.encode()).hexdigest()
 old=(ROOT/'dashboard/worker/index.js').read_text();fn=old[old.index('\nasync function ensureSavedDatabase(env)'):];template=(ROOT/'web/worker/template.js').read_text();worker=template+'\n// SAVED_SEED_START\nconst SAVED_ROWS = '+seed+';\nconst SEED_ID = '+json.dumps(seedid)+';'+fn
 (ROOT/'dashboard/worker/index.js').write_text(worker);h.c.dump(ROOT/'evidence/hosted/dashboard-seed.json',{'sha256':seedid,'summary':summary,'review_sample_size':len(chosen),'rows':len(rows),'bytes':len(worker.encode()),'source_database':'data/hosted/partial.sqlite'});print(json.dumps({'rows':len(rows),'bytes':len(worker.encode()),'completed':completed,'evidence_sample':len(chosen)}))
if __name__=='__main__':build()
