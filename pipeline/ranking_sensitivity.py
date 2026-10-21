"""Offline alternate rankings. Never writes baseline exports or classification state."""
import argparse,csv,gzip,hashlib,json
from collections import defaultdict
from decimal import Decimal,ROUND_HALF_UP
from pathlib import Path

def ranking(rows):
 buckets=defaultdict(list)
 for r in rows:
  if r['intent'] in ('complaint','cancellation'):buckets['issue-'+r['topic']].append(r['severity'])
 out=[]
 for issue,severities in buckets.items():
  n=len(severities);score=sum(severities)
  out.append(dict(issue_id=issue,complaint_count=n,severity_sum=score,priority_score=score,mean_severity=str((Decimal(score)/n).quantize(Decimal('.000001'),rounding=ROUND_HALF_UP))))
 return [dict(rank=i+1,**r) for i,r in enumerate(sorted(out,key=lambda r:(-r['severity_sum'],r['issue_id'])))]

def calculate(records,texts):
 unique=[];seen={};conflicts=0
 for r in records:
  text=texts[r['review_id']];fields=tuple(r[k] for k in ('topic','intent','severity','needs_review'))
  if text not in seen:seen[text]=fields;unique.append(r)
  elif seen[text]!=fields:conflicts+=1
 if conflicts:raise ValueError('Identical texts have conflicting classifications; resolve policy before interpreting deduplication')
 unflagged=[r for r in records if not r['needs_review']]
 scenarios={'baseline':records,'exact_text_once':unique,'exclude_needs_review':unflagged}
 return {name:{'retained_classifications':len(rows),'excluded_classifications':len(records)-len(rows),'ranking':ranking(rows)} for name,rows in scenarios.items()}

def run(root):
 root=Path(root);records_path=root/'grading/records.jsonl.gz';text_path=root/'grading/analysis_scope.csv'
 with gzip.open(records_path,'rt') as f:records=[r for r in map(json.loads,f) if r['status']=='completed']
 with text_path.open(newline='') as f:texts={r['review_id']:r['review_text'] for r in csv.DictReader(f)}
 assert len(records)==100000 and set(texts)=={r['review_id'] for r in records}
 result=calculate(records,texts)
 expected=list(csv.DictReader((root/'grading/ranking.csv').open()))
 assert [{k:str(v) for k,v in r.items()} for r in result['baseline']['ranking']]==expected
 for scenario in result.values():
  b={r['issue_id']:r for r in scenario['ranking']};p=b['issue-playback'];u=b['issue-usability']
  scenario['playback_vs_usability']={'playback_rank':p['rank'],'usability_rank':u['rank'],'playback_severity_sum':p['severity_sum'],'usability_severity_sum':u['severity_sum'],'playback_minus_usability':p['severity_sum']-u['severity_sum']}
 report={'scope':'100000-review partial cohort','paid_model_calls':0,'production_labels_changed':False,'baseline_export_changed':False,'exact_text_policy':'Exact original Python string equality; first source-order record retained once. No normalization. Conflicting duplicate classifications cause failure. These are distinct texts, not distinct people.','flag_policy':'Independent check excluding all needs_review=true records; no deduplication in this scenario. Flags are model outputs, not calibrated uncertainty.','source_sha256':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (records_path,text_path,root/'grading/ranking.csv')},'scenarios':result}
 out=root/'reports/ranking-sensitivity.json';out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:{x:v[x] for x in ('retained_classifications','excluded_classifications','playback_vs_usability')} for k,v in result.items()},indent=2));return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',default=str(Path(__file__).resolve().parents[1]));a=p.parse_args();run(a.root)
