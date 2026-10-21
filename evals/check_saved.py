"""Offline consistency check for authorized public evaluation outputs; no model inputs."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def check():
 manifest=json.loads((ROOT/'manifest.json').read_text())
 for name,digest in manifest['files_sha256'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
 expected={r['review_id']:r for r in json.loads((ROOT/'expected.json').read_text())};predictions={r['review_id']:r for r in json.loads((ROOT/'predictions.json').read_text())};comparisons=json.loads((ROOT/'comparisons.json').read_text());report=json.loads((ROOT/'report.json').read_text())
 assert len(expected)==len(predictions)==len(comparisons)==50
 correct={k:0 for k in ('topic','intent','severity')};triples=0;absolute=0
 for r in comparisons:
  rid=r['review_id'];h=expected[rid];p=predictions[rid]
  assert {k:v for k,v in h.items() if k!='review_id'}==r['human'] and p==r['prediction']
  errors=[k for k in correct if h[k]!=p[k]];assert errors==r['error_fields']
  for k in correct:correct[k]+=h[k]==p[k]
  triples+=not errors;absolute+=abs(h['severity']-p['severity'])
 assert {k:v/50 for k,v in correct.items()}==report['accuracy']=={'topic':.74,'intent':.8,'severity':.66}
 assert triples==22 and absolute/50==.38
 print('PASS: 50 expected labels, predictions and comparisons; original scores and hashes verified. No model calls.')
if __name__=='__main__':check()
