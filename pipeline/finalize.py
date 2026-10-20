"""Offline evidence reconciliation, usage tables and deliverable notes."""
import csv,json,sqlite3,time,gzip,shutil
from pathlib import Path
from core import ROOT,LABEL_CONFIG,dump
import sys
sys.path.insert(0,str(ROOT))
from cost.calculator import calculate

def main():
 # Preserve every recorded diagnostic attempt, separate from the clean pilot.
 diagnostic=[];allcalls={}
 for path in (ROOT/'data').glob('*.sqlite'):
  d=sqlite3.connect(path)
  try:
   for row in d.execute('SELECT payload FROM calls'):
    c=json.loads(row[0]);allcalls[c['request_id']]=c
    if path.name.startswith('failed'):diagnostic.append(c)
  finally:d.close()
 with (ROOT/'evidence/diagnostic_calls.jsonl').open('w') as f:
  for c in diagnostic:f.write(json.dumps(c,ensure_ascii=False)+'\n')
 with (ROOT/'evidence/all_calls.jsonl').open('w') as f:
  for c in sorted(allcalls.values(),key=lambda c:c['started_at']):f.write(json.dumps(c,ensure_ascii=False)+'\n')
 attempts=ROOT/'evidence/attempts';orphan=[]
 for p in attempts.glob('*-request.json'):
  req=json.loads(p.read_text());rid=req['request_id']
  if rid not in allcalls:orphan.append({'request_id':rid,'role':req['role'],'run_id':req['run_id'],'response_saved':(attempts/(rid+'-response.json')).exists(),'api_charge_usd':0,'status':'interrupted_before_final_log; local only; no external provider charge'})
 dump(ROOT/'evidence/attempt-reconciliation.json',{'total_unique_logged_attempts':len(allcalls),'diagnostic_attempts':len(diagnostic),'request_artifacts_without_final_call_row':orphan,'initial_unlogged_request':'see setup-failures.json','api_cost_usd':0,'local_compute_usd':None,'assistant_session_cost_usd':None,'hosting_usd':None})
 replay=calculate();dump(ROOT/'cost/replay.json',replay)
 fields=['request_id','run_id','stage','input_tokens','cached_input_tokens','output_tokens','api_usd','local_tokens_are_billed','seconds']
 with (ROOT/'cost/usage.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(replay['usage'])
 cold=replay['measured']['cold'];warm=replay['measured']['warm'];coverage=json.loads((ROOT/'evidence/full-coverage.json').read_text());check=json.loads((ROOT/'self-check.json').read_text());verification=json.loads((ROOT/'evidence/pilot-cold-verification.json').read_text())
 text=f'''# Cost and runtime: measured, projected, unavailable\n\nMeasured on the unchanged `cost_100.csv`: {cold['completed']} completed, {cold['remaining']} remaining; {cold['unique_nonempty_texts']} unique texts. Cold result cache was empty. Input SHA256: `{cold['input_sha256']}`.\n\n| Measurement | Cold | Warm |\n|---|---:|---:|\n| Wall-clock seconds | {cold['end_to_end_seconds']:.6f} | {warm['end_to_end_seconds']:.6f} |\n| Enrichment attempts | {cold['new_calls_by_role']['enrich']} | {warm['new_calls_by_role']['enrich']} |\n| Verification attempts | {cold['new_calls_by_role']['verify']} | {warm['new_calls_by_role']['verify']} |\n| Group attempts | {cold['new_calls_by_role']['group']} | {warm['new_calls_by_role']['group']} |\n| Memo attempts | {cold['new_calls_by_role']['memo']} | {warm['new_calls_by_role']['memo']} |\n| API charge USD | 0 | 0 |\n| Local compute USD | unknown | unknown |\n\nCold throughput: {100/cold['end_to_end_seconds']:.6f} input reviews/second. API charge per thousand inputs and per completed record is $0. API charge excludes local hardware/electricity. Under the clarified user budget, existing hardware, ordinary electricity and existing subscriptions do not count toward the cash cap; any new paid charge still counts. Independent verification disagreed on {len(verification['disagreements'])}/{verification['sample_size']} reviews. Subsequent 50-label human agreement is recorded separately in evaluation/REPORT.md; these pilot timings and outputs remain unchanged.\n\nSettings: Ollama gemma3:1b, Q4_K_M; digest in call logs; temperature 0, seed 42, context cap 16,384, output cap 1,024, unsupported effort parameter omitted, batch size 1, concurrency 1, fallback quota 0. Began with batches of 10; failed diagnostic formats were retained and excluded from the clean pilot. No provider prompt-cache discount is claimed.\n\nThe 500-review checkpoint is complete and refreshes the forecasts below. Its final resume segment timing excludes the earlier pilot and interrupted/resumed segments, which have their own logs and measurements; it is not a cold 500-review timing.\n\n| Scenario | Exact reuse | Distinct classifications | Estimated hours | API USD | Additional local cash USD | Economic total USD |\n|---|---|---:|---:|---:|---:|---|\n'''
 for s in replay['scenarios']:text+=f"| {s['name']} | {s['exact_text_reuse']} | {s['distinct_classifications']} | {s['estimated_elapsed_seconds']/3600:.3f} | 0 | 0 | unknown |\n"
 text+='''\nThese are stage-specific estimates, not full-run measurements. The eight-topic taxonomy bounds group and memo calls; verification is 10% capped at 10, fixed overhead is added once, retry assumptions are 2%/15%, fallback is zero. An unchanged warm run reuses downstream artifacts too. $4.90 caps model-call admission; no paid route exists. The user excludes existing hardware, ordinary electricity and existing subscriptions; the cash cap covers new charges, and no new paid service is enabled.\n\nScaling decision: hold 10,000/full gates. The actual injection test failed, classifier quality still requires repair and full-run quality is not established. Jev/cloud comparison is unavailable without keys; no imaginary quality, prices or usage are substituted.\n\nReplay: `python3 cost/calculator.py`. Tests demonstrate unchanged recorded pilot observations when projected volume changes, actual zero-API arithmetic under doubled rates, and nonzero rate scaling using a clearly synthetic billing fixture.\n'''
 (ROOT/'cost/report.md').write_text(text)
 packs=json.loads((ROOT/'evidence/full-partial-aggregates.json').read_text());memo='''# Decision memo — incomplete evidence\n\nDo not commit a Spotify roadmap priority from this run. The local classifier failed injection testing and made visibly unsupported interpretations; human evaluation is pending. Complete model validation before expanding coverage.\n\nThe following is a reproducible ranking of **classified rows only**, heavily affected by exact-text reuse and incomplete coverage. It is not a representative estimate of the full corpus.\n\n| Issue | Complaint/cancellation rows | Severity sum | Mean | Claim IDs |\n|---|---:|---:|---:|---|\n'''
 for p in packs:memo+=f"| {p['issue_id']} | {p['complaint_count']} | {p['severity_sum']} | {p['mean_severity']} | `{p['issue_id']}-complaint_count`, `{p['issue_id']}-severity_sum`, `{p['issue_id']}-mean_severity` |\n"
 memo+='''\nAll table claims refer to `grading/claims.csv`; priority equals severity sum. Saved AI-generated proposals and exact review citations are in `evidence/full-partial-recommendations.json`. They are candidates for human inspection, not validated product decisions. Generic criticism does not support a specific product fix.\n\nThe pilot suggests investigating premium-only playback restrictions and homescreen navigation as examples worth checking, while the generic `other` issue is not an actionable root cause. Compare billing/paywall behavior with playback reliability rather than treating all paid-user complaints as billing. Alternatives cannot be fairly prioritized until labels are reviewed and missing reviews are classified.\n\nThis historical, self-selected review dataset has no account revenue, plan tier or confirmed churn. Cancellation language is expressed intent. No revenue-at-risk, retention uplift, or causal impact is calculated.\n'''
 (ROOT/'MEMO.md').write_text(memo)
 print(json.dumps({'coverage':coverage,'audit_issue_counts':check['issue_counts'],'logged_attempts':len(allcalls),'unresolved_request_artifacts':len(orphan)}))
if __name__=='__main__':main()
