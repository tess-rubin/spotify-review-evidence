"""Embed a bounded, saved deployment seed. Runtime writes it to D1, then queries D1."""
import json,sqlite3,hashlib
from pathlib import Path
from core import LABEL_CONFIG
ROOT=Path(__file__).resolve().parents[1]
def build():
 d=sqlite3.connect(ROOT/'data/pilot.sqlite');d.row_factory=sqlite3.Row
 cold=json.loads((ROOT/'evidence/pilot-cold-measurement.json').read_text());warm=json.loads((ROOT/'evidence/pilot-warm-measurement.json').read_text())
 rows=[]
 for r in d.execute('SELECT s.*,l.result,l.cache_source_id FROM sources s JOIN labels l ON s.id=l.id WHERE config=?',(LABEL_CONFIG,)):
  v={'scope':'pilot','review_id':r['id'],'review_text':r['text'],'source_sha256':r['row_hash'],'status':'completed','label_config':LABEL_CONFIG,**json.loads(r['result'])};rows.append({'kind':'review','value':v})
 for r in d.execute('SELECT payload FROM aggregates WHERE config=?',(LABEL_CONFIG,)):rows.append({'kind':'aggregate','value':{'scope':'pilot',**json.loads(r[0])}})
 for r in json.loads((ROOT/'evidence/pilot-cold-recommendations.json').read_text())['recommendations']:rows.append({'kind':'recommendation','value':{'scope':'pilot',**r}})
 calls=[]
 for r in d.execute('SELECT payload FROM calls'):
  v=json.loads(r[0]);calls.append(v);rows.append({'kind':'call','value':{k:v.get(k) for k in ('request_id','run_id','role','review_ids','model','label_config','outcome','input_tokens','output_tokens','api_cost_usd','duration_seconds')}})
 f=sqlite3.connect(ROOT/'data/full.sqlite');full=f.execute('SELECT count(*) FROM labels WHERE config=?',(LABEL_CONFIG,)).fetchone()[0];f.close()
 summary={'status':'Partial execution: full corpus ingested; model failed prompt-injection testing. Rankings below cover only the 100-review pilot. Full classification and human evaluation remain incomplete.','full_source_rows':660622,'full_completed':full,'empty_quarantines':13,'pilot_completed':cold['completed'],'api_cost_usd':0,'cold_seconds':round(cold['end_to_end_seconds'],3),'warm_enrichment_calls':warm['new_calls_by_role']['enrich'],'calls':len(calls),'analysis_scope':'100-review cost pilot; not a full-corpus business conclusion','hosted_review_scope':'100 processed pilot reviews; full raw corpus remains in local SQLite'}
 rows.append({'kind':'snapshot','value':summary});seed=json.dumps(rows,ensure_ascii=False,separators=(',',':'));seedid=hashlib.sha256(seed.encode()).hexdigest()
 worker=(ROOT/'dashboard/worker/index.js').read_text();worker=worker.split('\n// SAVED_SEED_START')[0]
 # Seed only saved rows, not schema. Existing matching snapshot avoids all future writes.
 fn='''\n// SAVED_SEED_START\nconst SAVED_ROWS = SEED;\nconst SEED_ID = SEEDHASH;\nasync function ensureSavedDatabase(env){\n const old=await env.DB.prepare('SELECT payload FROM snapshots WHERE name = ?').bind('seed-version').first();if(old && old.payload===SEED_ID)return;\n const statements=[];for(const r of SAVED_ROWS){const v=r.value;\n if(r.kind==='review')statements.push(env.DB.prepare('INSERT OR REPLACE INTO reviews(scope,review_id,review_text,payload) VALUES(?,?,?,?)').bind(v.scope,v.review_id,v.review_text,JSON.stringify(v)));\n if(r.kind==='aggregate')statements.push(env.DB.prepare('INSERT OR REPLACE INTO issue_aggregates(scope,issue_id,severity_sum,payload) VALUES(?,?,?,?)').bind(v.scope,v.issue_id,v.severity_sum,JSON.stringify(v)));\n if(r.kind==='recommendation')statements.push(env.DB.prepare('INSERT OR REPLACE INTO recommendations(scope,issue_id,payload) VALUES(?,?,?)').bind(v.scope,v.issue_id,JSON.stringify(v)));\n if(r.kind==='call')statements.push(env.DB.prepare('INSERT OR REPLACE INTO call_evidence(request_id,payload) VALUES(?,?)').bind(v.request_id,JSON.stringify(v)));\n if(r.kind==='snapshot')statements.push(env.DB.prepare('INSERT OR REPLACE INTO snapshots(name,payload) VALUES(?,?)').bind('current',JSON.stringify(v)));}\n for(let i=0;i<statements.length;i+=50)await env.DB.batch(statements.slice(i,i+50));\n await env.DB.prepare('INSERT OR REPLACE INTO snapshots(name,payload) VALUES(?,?)').bind('seed-version',SEED_ID).run();}\n'''.replace('SEEDHASH',json.dumps(seedid)).replace('= SEED;','= '+seed+';')
 # Remove import mutation API: deployment seed is the sole data import path.
 if "if(u.pathname==='/api/import'" in worker:
  a=worker.index("if(u.pathname==='/api/import'");b=worker.index("return json({error:'Not found'}",a);worker=worker[:a]+worker[b:]
 if 'await ensureSavedDatabase(env);' not in worker:worker=worker.replace("if(u.pathname==='/api/summary'", "await ensureSavedDatabase(env);\nif(u.pathname==='/api/summary'")
 (ROOT/'dashboard/worker/index.js').write_text(worker+fn)
 (ROOT/'evidence/dashboard-seed.json').write_text(json.dumps({'sha256':seedid,'rows_by_kind':{k:sum(r['kind']==k for r in rows) for k in ('review','aggregate','recommendation','call','snapshot')},'summary':summary},indent=2)+'\n')
 print('Saved deployment seed:',len(rows),'rows,',len(seed),'characters')
if __name__=='__main__':build()
