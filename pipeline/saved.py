"""Offline merge, exact-text reuse and deterministic aggregation; no model calls."""
import argparse,json,sqlite3,time
from decimal import Decimal,ROUND_HALF_UP
from pathlib import Path
from core import dbopen,LABEL_CONFIG,dump,ROOT

def merge(source,target):
 d=dbopen(target);other=sqlite3.connect(source);other.row_factory=sqlite3.Row
 with d:
  for r in other.execute('SELECT l.*,s.row_hash,s.text_hash FROM labels l JOIN sources s ON s.id=l.id WHERE l.config=? AND l.cache_source_id IS NULL',(LABEL_CONFIG,)):
   orig=d.execute('SELECT row_hash FROM sources WHERE id=?',(r['id'],)).fetchone()
   if not orig or orig[0]!=r['row_hash']:raise ValueError('Source identity differs')
   d.execute('INSERT OR REPLACE INTO labels VALUES(?,?,?,NULL)',(r['id'],LABEL_CONFIG,r['result']))
   d.execute('INSERT OR IGNORE INTO cache VALUES(?,?,?,?)',(r['text_hash'],LABEL_CONFIG,r['id'],r['result']))
  for r in other.execute('SELECT * FROM calls'):d.execute('INSERT OR IGNORE INTO calls VALUES(?,?,?,?,?,?)',tuple(r))
  for r in other.execute('SELECT * FROM artifacts'):d.execute('INSERT OR IGNORE INTO artifacts VALUES(?,?)',tuple(r))
  matches=d.execute('SELECT s.id,c.source_id,c.result FROM sources s JOIN cache c ON s.text_hash=c.text_hash AND c.config=? JOIN sources original ON original.id=c.source_id AND original.text=s.text LEFT JOIN labels l ON l.id=s.id AND l.config=c.config WHERE l.id IS NULL',(LABEL_CONFIG,)).fetchall()
  d.executemany('INSERT INTO labels VALUES(?,?,?,?)',[(r['id'],LABEL_CONFIG,r['result'],r['source_id']) for r in matches])
 result={'completed':d.execute('SELECT count(*) FROM labels WHERE config=?',(LABEL_CONFIG,)).fetchone()[0],'direct_originals':d.execute('SELECT count(*) FROM labels WHERE config=? AND cache_source_id IS NULL',(LABEL_CONFIG,)).fetchone()[0],'cache_aliases':d.execute('SELECT count(*) FROM labels WHERE config=? AND cache_source_id IS NOT NULL',(LABEL_CONFIG,)).fetchone()[0],'total_source':d.execute('SELECT count(*) FROM sources').fetchone()[0]};dump(ROOT/'evidence/full-coverage.json',result);d.close();other.close();print(json.dumps(result))

def aggregate(db):
 d=dbopen(db);groups={}
 for r in d.execute('SELECT s.id,s.text,l.result FROM sources s JOIN labels l ON l.id=s.id WHERE l.config=? ORDER BY s.ordinal',(LABEL_CONFIG,)):
  v=json.loads(r['result'])
  if v['intent'] in ('complaint','cancellation'):groups.setdefault('issue-'+v['topic'],[]).append((r['id'],v))
 packs=[]
 with d:
  d.execute('DELETE FROM memberships WHERE config=?',(LABEL_CONFIG,));d.execute('DELETE FROM aggregates WHERE config=?',(LABEL_CONFIG,))
  for issue,items in groups.items():
   count=len(items);total=sum(v['severity'] for _,v in items);p={'issue_id':issue,'complaint_count':count,'severity_sum':total,'mean_severity':str((Decimal(total)/count).quantize(Decimal('.000001'),rounding=ROUND_HALF_UP)),'priority_score':total,'evidence':[{'review_id':rid,'quote':v['evidence_quote']} for rid,v in items[:2]]};packs.append(p)
   d.executemany('INSERT INTO memberships VALUES(?,?,?)',[(issue,rid,LABEL_CONFIG) for rid,_ in items]);d.execute('INSERT INTO aggregates VALUES(?,?,?)',(issue,LABEL_CONFIG,json.dumps(p)))
 packs.sort(key=lambda p:(-p['severity_sum'],p['issue_id']));d.close();return packs
if __name__=='__main__':
 p=argparse.ArgumentParser();s=p.add_subparsers(dest='cmd',required=True);a=s.add_parser('merge');a.add_argument('--source',required=True);a.add_argument('--target',required=True);a=s.add_parser('aggregate');a.add_argument('--db',required=True);a.add_argument('--out',required=True);a=p.parse_args()
 if a.cmd=='merge':merge(a.source,a.target)
 else:dump(a.out,aggregate(a.db))
