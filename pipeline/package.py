"""Package source and saved evidence; exclude raw corpus, databases and secrets."""
import hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
 files=[]
 for name in ('pipeline','tests','cost','grading','evaluation','evidence','dashboard','experiments','audit'):
  for p in (ROOT/name).rglob('*'):
   if p.is_file() and not any(x in p.relative_to(ROOT).parts for x in ('.git','node_modules','dist','__pycache__','data')) and not p.name.endswith(('.pyc','.tmp','.sqlite','.sqlite-wal','.sqlite-shm')) and p.name!='archive.json':files.append(p)
 for name in ('README.md','MEMO.md','LABELS.md','PROFESSOR_GUIDANCE.md','.gitignore','.env.example','self-check.json'):files.append(ROOT/name)
 files.extend(p for p in (ROOT/'supplied').iterdir() if p.is_file() and p.name!='spotify_reviews_18months.csv')
 path=ROOT/'spotify-evidence.zip'
 with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in sorted(files):z.write(p,p.relative_to(ROOT))
 report={'archive':path.name,'bytes':path.stat().st_size,'sha256':hashlib.file_digest(path.open('rb'),'sha256').hexdigest(),'files':len(files),'excluded':['raw source CSV','SQLite working databases','model weights stored by Ollama outside project','Git metadata','credentials','dependencies and generated deployment build']};(ROOT/'evidence/archive.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
