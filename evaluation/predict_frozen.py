"""Prediction worker: never reads human/ or evaluation result/answer files."""
import argparse,hashlib,json,sqlite3,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pipeline import core as c
ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('name',choices=['gemma-baseline','qwen-v2-frozen','qwen-v3-rubric-policy']);a=p.parse_args()
    frozen=json.loads((ROOT/'evaluation/frozen'/(a.name+'.json')).read_text());c.CONFIG.clear();c.CONFIG.update(frozen['config']);c.PROMPT=c.CONFIG['prompt'];c.LABEL_CONFIG=frozen['label_config']
    assert c.LABEL_CONFIG==hashlib.sha256(json.dumps(c.CONFIG,sort_keys=True).encode()).hexdigest()
    target=ROOT/'evaluation/predictions'/a.name;c.ROOT=target;target.mkdir(parents=True,exist_ok=True);source=ROOT/'evaluation/prediction-input.csv';db=target/'predictions.sqlite';c.ingest(source,db);d=c.dbopen(db);owner=a.name+'-golden-prediction';c.acquire(d,owner);start=time.monotonic();new=0
    try:
        # Copy only exact same-config predictions with matching source hashes from prior saved corpus/pilots.
        prior=ROOT/'data/full.sqlite' if a.name=='gemma-baseline' else ROOT/'experiments/qwen3-4b-v2/data/pilot.sqlite'
        old=sqlite3.connect(prior);old.row_factory=sqlite3.Row
        with d:
            for r in d.execute('SELECT * FROM sources').fetchall():
                v=old.execute('SELECT l.*,s.row_hash,s.text FROM labels l JOIN sources s ON s.id=l.id WHERE l.id=? AND l.config=?',(r['id'],c.LABEL_CONFIG)).fetchone()
                if v and v['row_hash']==r['row_hash']:
                    d.execute('INSERT OR IGNORE INTO labels VALUES(?,?,?,NULL)',(r['id'],c.LABEL_CONFIG,v['result']))
        old.close()
        reused=d.execute('SELECT count(*) FROM labels WHERE config=?',(c.LABEL_CONFIG,)).fetchone()[0]
        for r in d.execute('SELECT * FROM sources ORDER BY ordinal').fetchall():
            if d.execute('SELECT 1 FROM labels WHERE id=? AND config=?',(r['id'],c.LABEL_CONFIG)).fetchone():continue
            output=c.modelcall(d,'enrich',[r],'golden-'+a.name,'initial',4.9)
            with d:d.execute('INSERT INTO labels VALUES(?,?,?,NULL)',(r['id'],c.LABEL_CONFIG,json.dumps(output[r['id']],ensure_ascii=False)))
            new+=1
        records=[]
        for r in d.execute('SELECT s.id,s.row_hash,l.result FROM sources s JOIN labels l ON l.id=s.id AND l.config=? ORDER BY ordinal',(c.LABEL_CONFIG,)):
            records.append({'review_id':r['id'],'source_sha256':r['row_hash'],'status':'completed','label_config':c.LABEL_CONFIG,**json.loads(r['result'])})
        with (target/'records.jsonl').open('w') as f:
            for r in records:f.write(json.dumps(r,ensure_ascii=False)+'\n')
        with (target/'calls.jsonl').open('w') as f:
            for r in d.execute('SELECT payload FROM calls'):f.write(r[0]+'\n')
        c.dump(target/'run.json',{'name':a.name,'completed':len(records),'reused_same_config':reused,'new_enrichment_calls':new,'label_config':c.LABEL_CONFIG,'source_input_sha256':c.sha(source),'model_input_fields':['review_text'],'human_answers_read':False,'end_to_end_seconds':time.monotonic()-start,'additional_cash_usd':0})
        print(json.dumps({'name':a.name,'completed':len(records),'new_calls':new,'reused':reused}),flush=True)
    finally:
        with d:d.execute('DELETE FROM leases WHERE owner=?',(owner,))
        d.close()
