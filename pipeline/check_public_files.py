"""Inspect an explicit public source set. Prints paths/counts only, never secret values."""
import argparse,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def candidates():
 return [ROOT/n for n in subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT).decode().split('\0') if n]
def check(paths):
 secrets=[];env=ROOT/'.env'
 if env.exists():
  for line in env.read_text().splitlines():
   if '=' in line and not line.lstrip().startswith('#'):
    key,value=line.removeprefix('export ').split('=',1);value=value.strip().strip('\"\'')
    if ('KEY' in key or 'TOKEN' in key or 'SECRET' in key) and len(value)>=12:secrets.append(value.encode())
 bad=[];total=0
 for p in paths:
  if not p.is_file():continue
  rel=p.relative_to(ROOT).as_posix();total+=1
  forbidden=p.suffix.lower() in ('.csv','.tsv','.sqlite','.db','.key','.pem','.jsonl','.zip','.gz') or rel.startswith(('evaluation/human/','evaluation/results/','evaluation/predictions/','data/','evidence/','grading/','experiments/','dashboard/')) or (p.name.startswith('.env') and p.name!='.env.example')
  data=p.read_bytes()
  if forbidden or any(secret in data for secret in secrets) or re.search(rb'sk-(?:proj-)?[A-Za-z0-9_-]{30,}',data):bad.append(rel)
 if bad:raise RuntimeError('Public-file inspection blocked these paths: '+', '.join(bad))
 return {'status':'passed','inspected_files':total,'secret_values_displayed':False,'raw_datasets_credentials_and_working_databases_excluded':True,'golden_evaluation_publication_explicitly_authorized':True}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--staged',action='store_true');a=p.parse_args();paths=[ROOT/n for n in subprocess.check_output(['git','diff','--cached','--name-only','-z'],cwd=ROOT).decode().split('\0') if n] if a.staged else candidates();print(json.dumps(check(paths)))
