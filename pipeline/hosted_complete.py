"""Finalize a completed >=100k hosted partial run; invoked after successful classification.
No API key is printed or embedded; final memo/verification share the capped ledger.
"""
import gzip,json,shutil,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pipeline import hosted as h
from pipeline.hosted_finish import finish
ROOT=h.ROOT

def complete():
 h.activate();d=h.c.dbopen(h.STATE/'partial.sqlite');rows=h.selected_rows(d,'partial');ids={r[0] for r in d.execute('SELECT id FROM labels WHERE config=?',(h.LABEL_CONFIG,))}
 if len(ids)<100000 or not {r['id'] for r in rows}<=ids:raise RuntimeError('Not all 100000 target reviews completed; do not finalize')
 d.close();finish('partial');warm=h.run('partial',phase='resume')
 if warm['new_enrichment_calls']:raise RuntimeError('Unexpected warm enrichment calls')
 dest=ROOT/'grading';archive=ROOT/'evidence/historical-gemma-grading'
 if dest.exists() and not archive.exists():dest.rename(archive)
 dest.mkdir(exist_ok=True);h.c.export(h.STATE/'partial.sqlite',dest,ROOT/'supplied/spotify_reviews_18months.csv')
 with (dest/'records.jsonl').open('rb') as src,gzip.open(dest/'records.jsonl.gz','wb') as out:shutil.copyfileobj(src,out)
 (dest/'records.jsonl').unlink()
 for filename in ('checkpoint_before.json','checkpoint_after.json'):shutil.copyfile(ROOT/'evidence/hosted'/filename,dest/filename)
 if (archive/'ingestion.json').exists():shutil.copyfile(archive/'ingestion.json',dest/'ingestion.json')
 else:subprocess.run([sys.executable,str(ROOT/'supplied/check_submission.py'),'profile','--full',str(ROOT/'supplied/spotify_reviews_18months.csv'),'--out',str(dest/'ingestion.json')],check=True)
 # Preserve unavailable interrupted-request usage honestly; checker may flag it.
 calls=[json.loads(line) for line in (dest/'calls.jsonl').read_text().splitlines() if line.strip() and json.loads(line).get('label_config')==h.LABEL_CONFIG]
 for call in calls:
  if call['outcome']=='interrupted':call['original_outcome']='interrupted';call['outcome']='failed';call['usage_status']='unavailable_after_SIGINT; worst-case reservation retained'
 (dest/'calls.jsonl').write_text(''.join(json.dumps(c,ensure_ascii=False)+'\n' for c in calls))
 run=json.loads((dest/'run.json').read_text());run.update(completion_status='partial',target_classified=100000,hosted_completed=len(ids),label_config=h.LABEL_CONFIG,model=h.CONFIG['model'],historical_gemma_completed=66577,historical_gemma_included_in_hosted_count=False,entities_policy='empty arrays; no entity extraction',budget=h.budget_status(),grouping='deterministic code only; no grouping model call',scope_selection='first 100000 nonempty source-order rows excluding golden IDs and exact golden texts',deadline='2026-10-20T23:59:00-07:00');h.c.dump(dest/'run.json',run)
 if not (ROOT/'local-reference.json').exists():subprocess.run([sys.executable,str(ROOT/'supplied/check_submission.py'),'reference','--full',str(ROOT/'supplied/spotify_reviews_18months.csv'),'--analysis',str(ROOT/'supplied/spotify_reviews_18months.csv'),'--out',str(ROOT/'local-reference.json')],check=True)
 result=subprocess.run([sys.executable,str(ROOT/'supplied/check_submission.py'),'check','--reference',str(ROOT/'local-reference.json'),'--submission',str(dest),'--out',str(ROOT/'self-check.json')],capture_output=True,text=True);(ROOT/'evidence/hosted/checker-console.log').write_text(result.stdout+result.stderr)
 if not (ROOT/'self-check.json').exists():raise RuntimeError('Checker did not produce actual report')
 d=h.c.dbopen(h.STATE/'partial.sqlite');packs=h.aggregate(d);d.close();memo=json.loads((ROOT/'evidence/hosted/partial-memo.json').read_text());lines=['# Spotify partial-run memo','',f'{len(ids):,} hosted classifications out of 660,609 nonempty reviews. All 660,622 source rows were ingested/profiled. Historical Gemma classifications are separate. This source-order sample is not representative evidence of population prevalence or confirmed churn.','']
 for b in packs:
  rec=next(x for x in memo['recommendations'] if x['issue_id']==b['issue_id']);lines += [f"## {b['issue_id']}",f"{b['complaint_count']} complaints/cancellations; severity sum {b['severity_sum']}; mean severity {b['mean_severity']}. Claims: {b['issue_id']}-complaint_count, {b['issue_id']}-severity_sum, {b['issue_id']}-mean_severity.",rec['action'],f"Evidence review: {rec['review_id']}",'> '+rec['quote'].replace('\n','\n> '),'']
 (ROOT/'MEMO.md').write_text('\n'.join(lines));h.c.dump(ROOT/'evidence/hosted/completion.json',{'status':'local_deliverables_complete','completed':len(ids),'budget':h.budget_status(),'checker_returncode':result.returncode,'checker_issue_counts':json.loads((ROOT/'self-check.json').read_text()).get('issue_counts'), 'dashboard_deployment':'pending','public_github':'pending'})
 summary={'completed':len(ids),'full_rows':660622,'budget':h.budget_status(),'label_config':h.LABEL_CONFIG,'historical_gemma_separate':66577,'checker_issue_counts':json.loads((ROOT/'self-check.json').read_text()).get('issue_counts')}
 h.c.dump(ROOT/'cost/hosted-final-summary.json',summary)
 readme=ROOT/'README.md';text=readme.read_text().replace('**Status: hosted 100,000-review partial run in progress. Not a full-corpus classification.**',f'**Status: {len(ids):,} hosted reviews classified; local partial-run deliverables complete. Dashboard/repository publication pending. Not a full-corpus classification.**');text+='\nLatest completed hosted run: '+str(len(ids))+' reviews. Provider-usage-based recorded spend: $'+format(summary['budget']['spent_usd'],'.6f')+'; retained unknown reservations: $'+format(summary['budget']['reserved_or_unknown_usd'],'.6f')+'. See cost/hosted-final-summary.json and the actual self-check.json.\n';readme.write_text(text)
 from pipeline.prepare_hosted_dashboard import build as dashboard_seed
 dashboard_seed()
 from pipeline.package_hosted import build as package
 package()
 print(json.dumps({'local_deliverables':'complete','completed':len(ids),'budget':h.budget_status()}),flush=True)
if __name__=='__main__':
 try:complete()
 except RuntimeError as e:print(str(e),file=sys.stderr);sys.exit(2)
