"""One-command pipeline. Default: offline replay. Execution is opt-in and local-only."""
import argparse,sys,json,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pipeline.core import ingest,execute,export
from cost.calculator import calculate
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('input',nargs='?');p.add_argument('--execute-local',action='store_true');p.add_argument('--paid',action='store_true');p.add_argument('--spend-cap',type=float);p.add_argument('--db',default='data/custom.sqlite');p.add_argument('--out',default='experiments/custom-export');p.add_argument('--profile',choices=['qwen-v3','gemma-baseline'],default='qwen-v3');p.add_argument('--run-name',default='custom');a=p.parse_args()
 if a.paid:p.error('No paid provider adapter is enabled. Missing credentials and unmeasured costs prohibit paid execution; no provider calls were made.')
 if not a.execute_local:
  r=calculate();print(json.dumps({'measured':r['measured'],'scenarios':r['scenarios']},indent=2));sys.exit()
 if not a.input or a.spend_cap is None or not 0<a.spend_cap<5:p.error('Execution needs input CSV and --spend-cap strictly between 0 and 5')
 if Path(a.input).resolve().is_relative_to(Path(__file__).resolve().parents[1]/'evaluation/human'):p.error('Protected human-answer files cannot be used as inference inputs; use canonical source-only CSVs.')
 if Path(a.input).name in ('spotify_reviews_18months.csv','analysis_10000.csv'):p.error('Use pipeline/gate.py for 10,000 and full-corpus execution')
 if a.profile=='qwen-v3':
  from pipeline.classifier_profile import load_profile
  load_profile(a.profile)
 ingest(a.input,a.db);execute(a.db,a.input,a.spend_cap,name=a.run_name);export(a.db,a.out,a.input)
