"""Stage-aware checkpoint manifests and invalidation. Offline only."""
import argparse,hashlib,json,sqlite3,time
from pathlib import Path
try:from .core import LABEL_CONFIG,ROLE_VERSION,CONFIG,ROOT,dump
except ImportError:from core import LABEL_CONFIG,ROLE_VERSION,CONFIG,ROOT,dump
RANK_VERSION='severity-sum-desc-issue-id-asc-half-up-6-v1'
EDGES={'prepare':['enrich'],'enrich':['verify','group'],'verify':['release'],'group':['rank'],'rank':['memo'],'memo':['release'],'release':[]}
def affected(stage):
 out=set();todo=[stage]
 while todo:
  s=todo.pop()
  if s not in out:out.add(s);todo.extend(EDGES[s])
 return sorted(out)
def fingerprint(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
def versions():
 return {'prepare':'source-row-sha-contract-v1','enrich':LABEL_CONFIG,'verify':fingerprint([LABEL_CONFIG,ROLE_VERSION['verify']]),'group':fingerprint([LABEL_CONFIG,ROLE_VERSION['group']]),'rank':fingerprint([LABEL_CONFIG,ROLE_VERSION['group'],RANK_VERSION]),'memo':fingerprint([LABEL_CONFIG,ROLE_VERSION['group'],RANK_VERSION,ROLE_VERSION['memo']]),'release':'requires-human-review-v1'}
def save(db,out,input_sha256):
 d=sqlite3.connect(db);d.execute('BEGIN');labels=d.execute('SELECT id,config,result,cache_source_id FROM labels ORDER BY id,config').fetchall();rows=d.execute('SELECT id,row_hash,status,reason FROM sources ORDER BY ordinal').fetchall();quarantine=[r[0] for r in rows if r[2]=='quarantined'];payload={'version':'checkpoint-v2','created_at_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'input_sha256':input_sha256,'source_rows':len(rows),'source_fingerprint':fingerprint([(r[0],r[1]) for r in rows]),'classification_config':LABEL_CONFIG,'stage_versions':versions(),'completed_ids':[r[0] for r in labels if r[1]==LABEL_CONFIG],'quarantined_ids':quarantine,'output_references':{'database':str(Path(db).resolve()),'validated_labels_sha256':fingerprint(labels),'rankings':'grading/ranking.csv'},'in_flight_policy':'Reconcile persisted request/response artifacts before retry. No paid adapters enabled.','resume_requires':'matching source fingerprint and compatible stage versions'};d.rollback();d.close()
 out=Path(out)
 if out.exists():out.replace(out.with_suffix('.previous.json'))
 dump(out,payload);return payload
def compare(old,new):
 changed=[s for s in EDGES if old['stage_versions'].get(s)!=new['stage_versions'].get(s)]
 if old['source_fingerprint']!=new['source_fingerprint']:changed.append('prepare')
 invalid=sorted(set(s for stage in changed for s in affected(stage)))
 return {'changed_stages':sorted(set(changed)),'invalidate':invalid,'preserve':sorted(set(EDGES)-set(invalid)),'requires_new_model_calls':any(s in invalid for s in ('enrich','verify','group','memo'))}
if __name__=='__main__':
 p=argparse.ArgumentParser();s=p.add_subparsers(dest='cmd',required=True);a=s.add_parser('snapshot');a.add_argument('--db',required=True);a.add_argument('--input-sha256',required=True);a.add_argument('--out',required=True);a=s.add_parser('compare');a.add_argument('before');a.add_argument('after');a=s.add_parser('affected');a.add_argument('stage',choices=EDGES);a=p.parse_args()
 if a.cmd=='snapshot':save(a.db,a.out,a.input_sha256)
 elif a.cmd=='affected':print(json.dumps(affected(a.stage)))
 else:print(json.dumps(compare(json.loads(Path(a.before).read_text()),json.loads(Path(a.after).read_text())),indent=2))
