"""Offline usage/rate replay. No credentials, model clients or network."""
import argparse,csv,hashlib,json,math,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
def calculate(volume=100000,multiplier=1):
 measured=json.loads((ROOT/'cost/hosted-measured.json').read_text());rates=json.loads((ROOT/'cost/hosted-rates.json').read_text());projection=json.loads((ROOT/'cost/hosted-projection-inputs.json').read_text());calls=measured['calls'];roles={}
 for role in ('enrich','verify','memo'):
  selected=[c for c in calls if c['role']==role];inp=sum(c['input_tokens'] for c in selected);out=sum(c['output_tokens'] for c in selected);cached=sum(c.get('cached_input_tokens',0) for c in selected);cost=((inp-cached)*rates['input']+cached*rates['cached_input']+out*rates['output'])/1e6*multiplier
  roles[role]={'input_tokens':inp,'output_tokens':out,'cached_input_tokens':cached,'api_usd':cost,'seconds':sum(c['duration_seconds'] for c in selected),'attempts':len(selected)}
 n=measured['review_count'];perinput=roles['enrich']['input_tokens']/n;perout=roles['enrich']['output_tokens']/n;ratio=max(1,projection['target_mean_text_bytes']/projection['pilot_mean_text_bytes']);base=(perinput*ratio*rates['input']+perout*rates['output'])*volume/1e6*multiplier;downstream=(roles['verify']['api_usd']+roles['memo']['api_usd']);golden=base*50/volume if volume else 0;retry=.15
 past=projection.get('prior_spend_and_holds_excluding_this_pilot_usd',0)*multiplier;total=(base+downstream+golden)*1.15+measured['measured_pilot_api_usd']*multiplier+past;seconds=roles['enrich']['seconds']/n*volume*1.15+roles['verify']['seconds']+roles['memo']['seconds']
 return {'label_config':measured['label_config'],'pilot_input_sha256':measured['input_sha256'],'review_count':n,'input_tokens_per_review':perinput,'output_tokens_per_review':perout,'roles':roles,'recorded_pilot_measurements':measured,'rates_multiplier':multiplier,'projected_volume':volume,'target_to_pilot_text_byte_ratio':ratio,'base_100000_classification_usd':base,'conservative_100000_total_usd':total,'conservative_hours_without_reuse':seconds/3600,'retry_allowance':retry,'prior_spend_and_holds_usd':past,'pilot_and_golden_and_final_verification_memo_included':True,'fallback_quota':0,'exact_text_reuse_assumed':False,'projection_under_four_dollars':total<4,'hard_cap_usd':4.90,'unknown_new_infrastructure_usd':None,'cash_exclusions':['existing computer','ordinary electricity','existing subscriptions'],'caveat':'Projection from 100 short reviews; scales input conservatively by mean text bytes, charges all projected input at uncached rates, includes 15% retries and no reuse. Local full-corpus ingestion/export times excluded from API throughput; dollar values are provider-usage times dated rates, not a reconciled invoice.'}
def prepare():
 # Called after real pilot only; save portable measurement inputs independent of DB.
 from pipeline import hosted as h
 d=sqlite3.connect(h.STATE/'pilot.sqlite');calls=[json.loads(r[0]) for r in d.execute("SELECT payload FROM calls WHERE outcome='succeeded' AND json_extract(payload,'$.label_config')=?",(h.LABEL_CONFIG,))];cold=[json.loads(p.read_text()) for p in (ROOT/'evidence/hosted').glob('pilot-*-measurement.json')];cold=next(p for p in cold if p['new_enrichment_calls']>0 and p['label_config']==h.LABEL_CONFIG)
 reduced=[{k:c[k] for k in ('request_id','role','input_tokens','output_tokens','duration_seconds','api_cost_usd')}|{'cached_input_tokens':c['raw_provider_response']['usage'].get('prompt_tokens_details',{}).get('cached_tokens',0),'usage':c['raw_provider_response']['usage']} for c in calls]
 h.c.dump(ROOT/'cost/hosted-measured.json',{'label_config':h.LABEL_CONFIG,'review_count':100,'input_sha256':h.c.sha(ROOT/'supplied/cost_100.csv'),'cold_pipeline_seconds':cold['end_to_end_seconds'],'calls':reduced,'measured_pilot_api_usd':sum(c['api_cost_usd'] for c in calls),'usage_status':'provider reported; cash computed from dated published rates'})
 h.c.dump(ROOT/'cost/hosted-rates.json',h.RATES)
 pilot=[len(r['review_text'].encode()) for r in h.c.csv_rows(ROOT/'supplied/cost_100.csv')];full=h.c.dbopen(ROOT/'data/full.sqlite');rows=h.selected_rows(full,'partial');h.c.dump(ROOT/'cost/hosted-projection-inputs.json',{'target_count':len(rows),'target_mean_text_bytes':sum(len(r['text'].encode()) for r in rows)/len(rows),'pilot_mean_text_bytes':sum(pilot)/len(pilot),'golden_answer_values_read':False,'prior_spend_and_holds_excluding_this_pilot_usd':max(0,h.budget_status()['spent_usd']+h.budget_status()['reserved_or_unknown_usd']-sum(c['api_cost_usd'] for c in calls))});full.close()
 # Portable sanitized token/cost export; raw local calls remain ignored.
 h.c.dump(ROOT/'cost/hosted-pilot.json',calculate())
def main():
 p=argparse.ArgumentParser();p.add_argument('--prepare-from-pilot',action='store_true');p.add_argument('--volume',type=int,default=100000);p.add_argument('--rate-multiplier',type=float,default=1);a=p.parse_args()
 if a.prepare_from_pilot:prepare()
 r=calculate(a.volume,a.rate_multiplier);(ROOT/'cost'/('hosted-pilot.json' if a.prepare_from_pilot else 'hosted-replay.json')).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ('recorded_pilot_measurements','roles')},indent=2))
if __name__=='__main__':main()
