"""Recompute baseline ranking directly from saved export; no DB/model needed."""
import argparse,csv,gzip,json
from collections import defaultdict
from decimal import Decimal,ROUND_HALF_UP
from pathlib import Path

def rank(records,membership,out):
 opener=gzip.open if str(records).endswith('.gz') else open
 with opener(records,'rt',encoding='utf-8') as f:labels={r['review_id']:r for r in map(json.loads,f) if r['status']=='completed' and r['intent'] in ('complaint','cancellation')}
 groups=defaultdict(list);seen=set()
 for row in csv.DictReader(open(membership)):
  pair=(row['issue_id'],row['review_id'])
  if pair in seen:raise ValueError('Duplicate membership')
  seen.add(pair);v=labels[row['review_id']];groups[row['issue_id']].append(v['severity'])
 rows=[]
 for issue,ss in groups.items():
  total=sum(ss);n=len(ss);rows.append({'issue_id':issue,'complaint_count':n,'severity_sum':total,'mean_severity':str((Decimal(total)/n).quantize(Decimal('.000001'),rounding=ROUND_HALF_UP)),'priority_score':total})
 rows.sort(key=lambda r:(-r['severity_sum'],r['issue_id']))
 with open(out,'w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['rank','issue_id','complaint_count','severity_sum','mean_severity','priority_score']);w.writeheader();w.writerows(dict(r,rank=i+1) for i,r in enumerate(rows))
 return rows
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--records',required=True);p.add_argument('--membership',required=True);p.add_argument('--out',required=True);a=p.parse_args();rank(a.records,a.membership,a.out)
