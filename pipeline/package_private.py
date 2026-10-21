"""Build local-only human evaluation handoff. No network or model calls."""
import csv,hashlib,io,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def build():
 source=ROOT/'evaluation/results/hosted-luna';comparisons=json.loads((source/'comparison.json').read_text());labels=ROOT/'evaluation/human/labels.csv'
 assert len(comparisons)==50 and len(list(csv.DictReader(labels.open())))==50
 selected=json.loads((ROOT/'evaluation/polish-case-ids.json').read_text())
 cases=[next(r for r in comparisons if r['review_id']==rid) for rid in selected];assert all(r['error_fields'] for r in cases)
 files=[labels,ROOT/'evaluation/polish-case-ids.json']+[source/n for n in ('comparison.json','report.json','intent-confusion.csv','topic-confusion.csv')]
 path=ROOT/'spotify-private-evaluation.zip'
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
  for p in files:z.write(p,p.relative_to(ROOT))
  z.writestr('private-error-cases.json',json.dumps({'purpose':'Post-run diagnostic cases only; no tuning or label changes. Public memo contains only mechanisms, no private pairs.','cases':cases},ensure_ascii=False,indent=2))
  z.writestr('PRIVATE-README.txt','PRIVATE: 50 original human labels, 50 original frozen hosted per-review comparisons, aggregate evaluation and three selected diagnostic cases. Original production scores and labels remain unchanged. Human annotations can require contract-based review; do not assume every disagreement is a model error. No human answers were sent to a model. A previously disclosed golden-informed candidate was rejected and never used for production. No credentials included. Deliver only through an instructor-approved private course upload or approved private transfer; do not attach to a public GitHub release.\n')
 path.chmod(0o600)
 with zipfile.ZipFile(path) as z:
  assert z.testzip() is None and z.read('evaluation/human/labels.csv')==labels.read_bytes()
  assert json.loads(z.read('evaluation/results/hosted-luna/comparison.json'))==comparisons
  assert len(z.namelist())==8
 report={'status':'passed','private_archive':path.name,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'files':8,'human_labels_rows':50,'original_per_review_comparisons':50,'selected_private_diagnostic_cases':3,'source_labels_identical':True,'source_comparisons_identical':True,'publicly_uploaded':False,'credentials_included':False}
 (ROOT/'reports/private-package.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':build()
