"""Sanitized grader release. Never include human answers, .env or working databases."""
import hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def build():
 files=[]
 for base in ('grading','reports'):
  files.extend(p for p in (ROOT/base).rglob('*') if p.is_file() and p.name!='public-artifact-scan.json')
 for name in ('records.jsonl.gz','run.json','ingestion.json'):
  p=ROOT/'evidence/hosted/full-accounting'/name
  if p.exists():files.append(p)
 for name in ('resume.cast','resume.html','resume-check.json','checkpoint_before.json','checkpoint_after.json','partial-verify.json','partial-verification-comparison.json','partial-memo.json','security-check.json','security-cases-before.json','review-trace.json','dashboard-consistency.json'):
  p=ROOT/'evidence/hosted'/name
  if p.exists():files.append(p)
 files.extend(p for p in (ROOT/'cost').glob('hosted-*') if p.is_file() and not p.name.endswith('console.json'))
 for name in ('README.md','MEMO.md','LABELS.md','cost/README.md'):
  files.append(ROOT/name)
 secrets=[]
 for line in (ROOT/'.env').read_text().splitlines():
  if '=' in line and not line.lstrip().startswith('#'):
   k,v=line.removeprefix('export ').split('=',1);v=v.strip().strip('\"\'')
   if ('KEY' in k or 'TOKEN' in k or 'SECRET' in k) and len(v)>12:secrets.append(v.encode())
 for p in files:
  rel=p.relative_to(ROOT).as_posix()
  if rel.startswith('evaluation/') or p.suffix in ('.sqlite','.db') or p.name.startswith('.env'):raise RuntimeError('Private path in release: '+rel)
  data=p.read_bytes()
  if any(s in data for s in secrets):raise RuntimeError('Secret content in release path: '+rel)
 path=ROOT/'spotify-public-evidence.zip'
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in sorted(set(files)):z.write(p,p.relative_to(ROOT))
 report={'status':'passed','archive':path.name,'bytes':path.stat().st_size,'sha256':hashlib.file_digest(path.open('rb'),'sha256').hexdigest(),'files':len(set(files)),'human_answer_files_excluded':True,'credentials_and_databases_excluded':True,'contains_processed_source_text':True,'scope':'explicit 100000-review partial analysis plus full-source accounting'}
 (ROOT/'reports/public-artifact-scan.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));return report
if __name__=='__main__':build()
