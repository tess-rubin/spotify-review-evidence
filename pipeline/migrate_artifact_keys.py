"""Migrate identical artifacts to dependency-aware identities, without inference."""
import hashlib,json,sqlite3
from pathlib import Path
from core import ROLE_VERSION,LABEL_CONFIG,ROOT,dump
from checkpoints import versions
counts={}
for path in (ROOT/'data').glob('*.sqlite'):
 if path.name.startswith('failed') or path.name=='synthetic-eval.sqlite':continue
 d=sqlite3.connect(path);d.row_factory=sqlite3.Row;count=0
 with d:
  for r in d.execute('SELECT payload FROM calls').fetchall():
   call=json.loads(r[0]);role=call['role']
   if role=='enrich' or call['outcome']!='succeeded' or call.get('label_config')!=LABEL_CONFIG:continue
   if role=='verify':
    rows=[d.execute('SELECT id,text FROM sources WHERE id=?',(rid,)).fetchone() for rid in call['review_ids']]
    if any(x is None for x in rows):continue
    payload=[dict(x) for x in rows]
   else:payload=call['input']
   old=hashlib.sha256(json.dumps([role,ROLE_VERSION[role],LABEL_CONFIG,payload],sort_keys=True).encode()).hexdigest();new=hashlib.sha256(json.dumps([role,versions()[role],LABEL_CONFIG,payload],sort_keys=True).encode()).hexdigest();value=d.execute('SELECT value FROM artifacts WHERE key=?',(old,)).fetchone()
   if value:d.execute('INSERT OR IGNORE INTO artifacts VALUES(?,?)',(new,value[0]));count+=1
 counts[path.name]=count;d.close()
dump(ROOT/'evidence/artifact-key-migration.json',{'reason':'Add dependency versions to artifact identity while preserving identical saved work','new_model_calls':0,'artifact_counts':counts})
