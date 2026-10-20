"""Fresh rubric-synthetic check plus blind real-review holdout; no golden answers read."""
import argparse,csv,hashlib,json,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pipeline import hosted as h
ROOT=h.ROOT;OUT=ROOT/'evaluation/fresh-holdout'
def prepare():
 if (OUT/'freeze.json').exists():raise RuntimeError('Fresh holdout already frozen; do not rewrite')
 OUT.mkdir(parents=True,exist_ok=True)
 examples=[
 ('access','complaint',4,'Every sign-in attempt fails; I cannot enter my account at all.'),('access','praise',1,'Signing in with my password works flawlessly.'),('access','request',1,'Please offer passkeys as another sign-in option.'),
 ('usability','complaint',2,'The toolbar colors are ugly, although all the buttons work.'),('usability','complaint',3,'Reordering my queue fails, but I can still listen to every song.'),('usability','request',1,'I would like custom icons for playlist folders.'),
 ('playback','complaint',4,'Not a single track produces any sound; I cannot listen to anything.'),('playback','complaint',3,'The sound stutters briefly but the tracks continue.'),('playback','praise',1,'Tracks play smoothly from start to finish.'),
 ('downloads','complaint',4,'All saved downloads fail completely when I disconnect; offline listening is impossible.'),('downloads','complaint',3,'Some downloads fail, but the remaining saved tracks work offline.'),('downloads','request',1,'Please add a preference for the location of downloaded files.'),
 ('catalog','complaint',3,'A particular album disappeared from the library, though I can listen to other artists.'),('catalog','praise',1,'The collection includes an impressive variety of music genres.'),('catalog','complaint',3,'Search misses tracks until I retry, and my downloads also fail until I retry; both eventually work.'),
 ('billing','complaint',5,'A fraudulent subscription transaction emptied my bank account and caused serious financial loss.'),('billing','complaint',2,'The monthly subscription price annoys me, but everything works.'),('billing','cancellation',2,'I am cancelling my membership because the price is too high.'),
 ('support','praise',1,'The help desk answered my question promptly and politely.'),('support','request',1,'Please offer an option for support to call me back.'),('support','complaint',3,'Support repeatedly sends irrelevant replies instead of answering my question; the app itself still works.'),
 ('other','praise',1,'I gave a low star rating last year; today I love the app and everything works perfectly.'),('other','complaint',2,'I am furious with this app, but I have no specific fault to describe.'),('access','complaint',4,'The album search is slow, and I cannot sign in at all, so I cannot use my account.')]
 cases=[{'id':'fresh-synthetic-'+str(i),'text':text,'expected':{'topic':topic,'intent':intent,'severity':severity}} for i,(topic,intent,severity,text) in enumerate(examples)];h.c.dump(OUT/'synthetic-cases.json',cases)
 ids=set();texts=set()
 for fn in ('golden_50_to_label.csv','cost_100.csv','checkpoint_500.csv'):
  for r in h.c.csv_rows(ROOT/'supplied'/fn):ids.add(r['review_id']);texts.add(hashlib.sha256(r['review_text'].encode()).hexdigest())
 rows=[];seen=set()
 for i,r in enumerate(h.c.csv_rows(ROOT/'supplied/analysis_10000.csv')):
  sha=hashlib.sha256(r['review_text'].encode()).hexdigest()
  if i<1000 or r['review_id'] in ids or sha in texts or sha in seen or not r['review_text'].strip():continue
  rows.append(r);seen.add(sha)
  if len(rows)==50:break
 if len(rows)!=50:raise ValueError('Could not reserve 50 disjoint real holdout reviews')
 with (OUT/'blind-human-labels.csv').open('w',newline='') as f:
  fields=['review_id','review_text','human_topic','human_intent','human_severity'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({'review_id':r['review_id'],'review_text':r['review_text'],'human_topic':'','human_intent':'','human_severity':''} for r in rows)
 with (OUT/'source-only.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 h.c.dump(OUT/'freeze.json',{'label_config':h.LABEL_CONFIG,'synthetic_sha256':h.c.sha(OUT/'synthetic-cases.json'),'real_source_sha256':h.c.sha(OUT/'source-only.csv'),'synthetic_count':24,'real_count':50,'real_human_evaluation':'pending blind human labels','human_golden_answers_read':False,'scope':'New synthetic rubric cases are a functional check, not population/human accuracy. Real holdout selected from analysis10000 excluding prior checkpoint500, cost100 and golden IDs and exact text hashes. No prompt revision selected from this check.'})
def run():
 freeze=json.loads((OUT/'freeze.json').read_text())
 if freeze['label_config']!=h.LABEL_CONFIG or freeze['synthetic_sha256']!=h.c.sha(OUT/'synthetic-cases.json'):raise RuntimeError('Frozen holdout/config changed')
 if (OUT/'synthetic-report.json').exists():raise RuntimeError('Do not rerun a scored holdout')
 cases=json.loads((OUT/'synthetic-cases.json').read_text());rows=[{'id':c['id'],'text':c['text'],'text_hash':hashlib.sha256(c['text'].encode()).hexdigest()} for c in cases];budget=h.budget_status();h.CAP=min(h.CAP,math.floor((budget['spent_usd']+budget['reserved_or_unknown_usd']+.01)*1e6));h.acquire();d=h.c.dbopen(h.STATE/'fresh-holdout.sqlite')
 try:result=h.request(d,rows,'fresh-holdout-once',role='verify')
 finally:d.close();h.release()
 scores={f:sum(result[c['id']][f]==c['expected'][f] for c in cases)/len(cases) for f in ('topic','intent','severity')};correct=sum(all(result[c['id']][f]==c['expected'][f] for f in scores) for c in cases);errors=[{'id':c['id'],'expected':c['expected'],'prediction':result[c['id']]} for c in cases if any(result[c['id']][f]!=c['expected'][f] for f in scores)]
 report={'count':len(cases),'accuracy':scores,'all_three_correct':correct,'errors':errors,'label_config':h.LABEL_CONFIG,'new_api_usd':h.budget_status()['spent_usd']-budget['spent_usd'],'interpretation':'Fresh, pre-frozen synthetic rubric check only. Not a new human-labeled accuracy estimate; the 50 fresh real reviews are pending blind human labeling.','prompt_changed_after_check':False};h.c.dump(OUT/'synthetic-report.json',report);print(json.dumps(report,indent=2))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('action',choices=['prepare','run']);args=a.parse_args();prepare() if args.action=='prepare' else run()
