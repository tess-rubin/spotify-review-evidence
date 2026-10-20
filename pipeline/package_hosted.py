"""Local submission archive. Never upload this evidence archive to the public code repo."""
import hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def build():
 if not (ROOT/'evidence/hosted/completion.json').exists():raise RuntimeError('Hosted completion evidence missing')
 files=[]
 for base in ('grading','evidence/hosted'):
  for p in (ROOT/base).rglob('*'):
   if p.is_file() and not any(x in p.parts for x in ('preflight-grading','__pycache__')) and p.suffix not in ('.sqlite','.db'):files.append(p)
 for p in (ROOT/'cost').glob('hosted*'):
  if p.is_file():files.append(p)
 files.append(ROOT/'cost/README.md')
 for base in ('pipeline','audit','tests'):
  files.extend(p for p in (ROOT/base).rglob('*') if p.is_file() and p.suffix in ('.py','.md','.sh','.json') and '__pycache__' not in p.parts)
 for fn in ('README.md','MEMO.md','LABELS.md','PROFESSOR_GUIDANCE.md','self-check.json','supplied/check_submission.py','supplied/manifest.json','supplied/GRADING_CONTRACT.md','supplied/COST_CALCULATOR.md','evaluation/hosted-summary.json','evaluation/prompt-trial/adoption-decision.json','evaluation/prompt-trial/after.json','evaluation/fresh-holdout/freeze.json','evaluation/fresh-holdout/synthetic-cases.json','evaluation/fresh-holdout/synthetic-report.json','evaluation/fresh-holdout/blind-human-labels.csv'):files.append(ROOT/fn)
 path=ROOT/'spotify-hosted-partial-submission.zip'
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in sorted(set(files)):
   if p.exists():z.write(p,p.relative_to(ROOT))
 report={'archive':path.name,'bytes':path.stat().st_size,'sha256':hashlib.file_digest(path.open('rb'),'sha256').hexdigest(),'no_credentials':True,'no_human_answer_files':True,'public_github_upload':False};(ROOT/'evidence/hosted/archive.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));return report
if __name__=='__main__':build()
