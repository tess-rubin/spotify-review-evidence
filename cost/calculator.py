"""Offline calculator. Never imports a network client or calls a model."""
import argparse,csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def calculate(volume=660609,rate_multiplier=1):
 rates={r['item']:float(r['price_per_unit'])*rate_multiplier for r in csv.DictReader(open(ROOT/'cost/rates.csv')) if r['category']=='api'}
 calls=[json.loads(s) for s in (ROOT/'cost/pilot_calls.jsonl').read_text().splitlines() if s.strip()] if (ROOT/'cost/pilot_calls.jsonl').exists() else []
 measurements={p.name.replace('-measurement.json',''):json.loads(p.read_text()) for p in (ROOT/'evidence').glob('*-measurement.json')}
 cold=measurements.get('pilot-cold');warm=measurements.get('pilot-warm')
 # Billing fields are mutually exclusive. Local tokens are reported for throughput, not billed API tokens.
 costs={};usage=[]
 for c in calls:
  billed=c.get('billing_items',[])
  charge=sum(float(b['units'])*rates[b['item']] for b in billed)
  costs[c['role']]=costs.get(c['role'],0)+charge
  usage.append({'request_id':c['request_id'],'run_id':c['run_id'],'stage':c['role'],'input_tokens':c.get('input_tokens'),'cached_input_tokens':c.get('raw_provider_response',{}).get('prompt_eval_cached_count'),'output_tokens':c.get('output_tokens'),'api_usd':charge,'local_tokens_are_billed':False,'seconds':c['duration_seconds']})
 scenarios=[]
 if cold:
  latest=measurements.get('analysis10000') or measurements.get('checkpoint500') or cold
  projection_calls=calls
  call_source=ROOT/'cost'/('analysis10000_calls.jsonl' if 'analysis10000' in measurements else 'checkpoint500_calls.jsonl')
  if latest is not cold:
   if call_source.exists():projection_calls=[json.loads(line) for line in call_source.read_text().splitlines() if line.strip()]
   else:latest=cold # portable replay falls back honestly to the saved cold pilot
  byrole={r:[c for c in projection_calls if c['run_id']==latest['run_id'] and c['role']==r] for r in ('enrich','verify','group','memo')}
  for reuse in (False,True):
   unique=round(volume*484189/660609) if reuse else volume
   for kind,retries,verify_rate in [('base',0.02,0.1),('conservative',0.15,0.1)]:
    stages={}
    for role in byrole:
     cs=byrole[role];total_seconds=sum(c['duration_seconds'] for c in cs);sent=sum(len(c['review_ids']) for c in cs)
     if role=='enrich':
      work=unique;denom=latest.get('new_enrichment_results',sent);total_seconds=latest.get('stage_seconds',{}).get('enrich',total_seconds)
     elif role=='verify':work=min(10,max(1,round(volume*verify_rate)));denom=sent
     elif role=='group':work=8;denom=len(cs)
     else:work=8;denom=len(cs)
     stages[role]={'work_units':work,'estimated_seconds':total_seconds/denom*work*(1+retries) if denom else None,'api_usd':0 if cs and all(c.get('api_cost_usd')==0 for c in cs) else None,'retry_fraction':retries,'fallback_fraction':0}
    known=all(v['estimated_seconds'] is not None for v in stages.values());secs=sum(v['estimated_seconds'] or 0 for v in stages.values())+12
    scenarios.append({'name':kind,'exact_text_reuse':reuse,'projected_nonempty_rows':volume,'distinct_classifications':unique,'stages':stages,'fixed_seconds':12,'estimated_elapsed_seconds':secs if known else None,'api_usd':0,'local_compute_usd':None,'infrastructure_usd':None,'budget_usd':4.90,'economic_total_cost_known':False,'projected_additional_local_execution_cash_usd':0,'cash_budget_exclusions':['existing computer','ordinary electricity','existing subscriptions'],'budget_warning':'New paid charges must remain below $5. Existing computer, ordinary electricity and existing subscriptions are excluded by the user; no paid API route is enabled.','projection_measurement_run_id':latest['run_id'],'verification_fraction':verify_rate,'verification_cap':10,'fallback_quota':0})
 return {'measured':{'cold':cold,'warm':warm,'api_subtotal_usd':sum(costs.values()),'api_cost_by_stage':costs,'local_compute_usd':None,'billing_reconciliation':'No external provider called; local execution has no API bill. Existing computer, ordinary electricity and existing subscriptions are excluded from the user cash cap; any new charges still count.'},'budget_policy':json.loads((ROOT/'cost/budget_policy.json').read_text()) if (ROOT/'cost/budget_policy.json').exists() else None,'scenarios':scenarios,'usage':usage,'rates_multiplier':rate_multiplier,'projected_volume':volume}
def main():
 p=argparse.ArgumentParser();p.add_argument('--volume',type=int,default=660609);p.add_argument('--rate-multiplier',type=float,default=1);p.add_argument('--out',default='cost/replay.json');a=p.parse_args();r=calculate(a.volume,a.rate_multiplier);Path(a.out).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ('usage','measured')},indent=2))
if __name__=='__main__':main()
