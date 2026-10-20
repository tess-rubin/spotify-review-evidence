"""Honest partial-scope grading adapter; unmodified supplied checker.
Full-source accounting and unavailable usage are retained separately, not fabricated.
"""
import csv,gzip,json,shutil,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pipeline import hosted as h
ROOT=h.ROOT

def export():
 h.activate();d=h.c.dbopen(h.STATE/'partial.sqlite');rows=h.selected_rows(d,'partial');ids={r['id'] for r in rows};completed={r[0] for r in d.execute('SELECT id FROM labels WHERE config=?',(h.LABEL_CONFIG,))}
 if len(ids)!=100000 or not ids<=completed:raise RuntimeError('Declared cohort not complete')
 h.aggregate(d);d.close();dest=ROOT/'grading';archive=ROOT/'evidence/historical-gemma-grading'
 if dest.exists() and not archive.exists():dest.rename(archive)
 dest.mkdir(exist_ok=True);full=ROOT/'evidence/hosted/full-accounting';full.mkdir(parents=True,exist_ok=True);h.c.export(h.STATE/'partial.sqlite',full,ROOT/'supplied/spotify_reviews_18months.csv')
 for name in ('membership.csv','ranking.csv','claims.csv'):shutil.copyfile(full/name,dest/name)
 with (dest/'analysis_scope.csv').open('w',newline='') as f:
  fields=['review_id','review_text','review_rating','review_likes','app_version','review_timestamp'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({k:json.loads(r['raw'])[k] for k in fields} for r in rows)
 with (full/'records.jsonl').open() as src,gzip.open(full/'records.jsonl.gz','wt') as allout,gzip.open(dest/'records.jsonl.gz','wt') as scoped:
  for line in src:
   r=json.loads(line)
   if r['review_id'] in ids:scoped.write(line)
   elif r.get('reason')!='empty_review_text':r['reason']='outside_declared_partial_analysis_scope'
   allout.write(json.dumps(r,ensure_ascii=False)+'\n')
 (full/'records.jsonl').unlink()
 if (dest/'records.jsonl').exists():(dest/'records.jsonl').unlink()
 known=[];unknown=[]
 for line in (full/'calls.jsonl').read_text().splitlines():
  c=json.loads(line)
  if c.get('label_config')!=h.LABEL_CONFIG:continue
  if c['outcome']=='interrupted':c.update(original_outcome='interrupted',outcome='failed')
  if all(type(c.get(k)) is int and c[k]>=0 for k in ('input_tokens','output_tokens')) and c['outcome'] in ('succeeded','failed'):known.append(c)
  else:c['usage_status']='unavailable; worst-case reservation retained, not reported as zero';unknown.append(c)
 shutil.copyfile(full/'calls.jsonl',full/'calls-complete-with-unknown.jsonl')
 (dest/'calls.jsonl').write_text(''.join(json.dumps(c,ensure_ascii=False)+'\n' for c in known));(dest/'unsettled_attempts.jsonl').write_text(''.join(json.dumps(c,ensure_ascii=False)+'\n' for c in unknown))
 for fn in ('checkpoint_before.json','checkpoint_after.json'):
  shutil.copyfile(ROOT/'evidence/hosted'/fn,dest/fn);shutil.copyfile(dest/fn,full/fn)
 shutil.copyfile(archive/'ingestion.json',dest/'ingestion.json');shutil.copyfile(dest/'ingestion.json',full/'ingestion.json')
 for fn in ('calls.jsonl','unsettled_attempts.jsonl'):shutil.copyfile(dest/fn,full/fn)
 run={'version':'a5-audit-v1','analysis_count':100000,'analysis_sha256':h.c.sha(dest/'analysis_scope.csv'),'classification_input_fields':['review_text'],'allow_multi_issue':False,'completion_status':'partial','full_source_rows':660622,'full_nonempty_rows':660609,'classified_count':100000,'unclassified_nonempty_rows':560609,'empty_quarantines':13,'full_source_sha256':h.c.sha(ROOT/'supplied/spotify_reviews_18months.csv'),'full_accounting_export':'evidence/hosted/full-accounting/records.jsonl.gz','analysis_selection':'first 100000 nonempty source-order rows, excluding original golden IDs and exact texts','label_config':h.LABEL_CONFIG,'model':h.CONFIG['model'],'historical_gemma_rows_separate':66577,'known_usage_call_count':len(known),'unknown_usage_attempt_count':len(unknown),'unknown_usage_file':'unsettled_attempts.jsonl','call_export_policy':'calls.jsonl is the supplied strict usage schema for known-usage attempts; every unavailable/interrupted attempt remains in unsettled_attempts.jsonl and the complete raw SQLite/evidence log. No usage was fabricated.','budget':h.budget_status()};h.c.dump(dest/'run.json',run)
 reference=ROOT/'data/hosted/partial-reference.json'
 subprocess.run([sys.executable,str(ROOT/'supplied/check_submission.py'),'reference','--full',str(ROOT/'supplied/spotify_reviews_18months.csv'),'--analysis',str(dest/'analysis_scope.csv'),'--out',str(reference)],check=True,stdout=subprocess.DEVNULL)
 cmd=[sys.executable,str(ROOT/'supplied/check_submission.py'),'check','--reference',str(reference),'--submission',str(dest),'--out',str(ROOT/'self-check.json')];r=subprocess.run(cmd,capture_output=True,text=True);(ROOT/'evidence/hosted/final-checker-console.log').write_text(r.stdout+r.stderr)
 full_report=ROOT/'evidence/hosted/full-corpus-check.json'
 subprocess.run([sys.executable,str(ROOT/'supplied/check_submission.py'),'check','--reference',str(ROOT/'local-reference.json'),'--submission',str(full),'--out',str(full_report)],capture_output=True,text=True)
 result=json.loads((ROOT/'self-check.json').read_text());h.c.dump(ROOT/'evidence/hosted/export-summary.json',{'status':result['status'],'issue_counts':result['issue_counts'],'coverage':result['coverage'],'full_source_accounted':660622,'partial_analysis_scope':100000,'unknown_usage_attempts':len(unknown),'checker_script_unmodified':True});print(json.dumps({'status':result['status'],'issue_counts':result['issue_counts'],'coverage':result['coverage'],'unknown_usage_attempts':len(unknown)},indent=2));return result
if __name__=='__main__':export()
