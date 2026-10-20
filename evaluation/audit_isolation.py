"""Audit saved inference payloads and direct reuse lineage; never calls a model."""
import csv,hashlib,json,sqlite3,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
ROOT=Path(__file__).resolve().parents[1]

def canonical_prompt(frozen):
    return frozen['config']['prompt'].replace('Quote an EXACT nonempty substring from each text. Entities may be empty.','Evidence and entities are extracted by code; do not return them.').replace('exactly all supplied review_id values.','Return one classification object; do not return review_id or a results array.')

def check_call(call,frozen,rid,text):
    assert call['role']=='enrich' and call['review_ids']==[rid]
    assert call['input']=={'review_text':text}
    assert call['actual_prompt']==canonical_prompt(frozen)
    assert call['label_config']==frozen['label_config'] and call['settings']==frozen['config']

def trace_reuse(database,record,source,frozen):
    """Follow exactly one cache hop and verify original source and successful call."""
    d=sqlite3.connect('file:'+str(Path(database).resolve())+'?mode=ro',uri=True);d.row_factory=sqlite3.Row
    try:
        rid=record['review_id'];config=frozen['label_config']
        old=d.execute('SELECT l.*,s.row_hash,s.text,s.text_hash FROM labels l JOIN sources s ON s.id=l.id WHERE l.id=? AND l.config=?',(rid,config)).fetchone()
        assert old is not None and old['row_hash']==record['source_sha256'] and old['text']==source['review_text']
        result=json.loads(old['result']);assert all(record[k]==v for k,v in result.items())
        origin=old['cache_source_id'] or rid
        direct=d.execute('SELECT l.*,s.text,s.text_hash FROM labels l JOIN sources s ON s.id=l.id WHERE l.id=? AND l.config=?',(origin,config)).fetchone()
        assert direct is not None and direct['cache_source_id'] is None
        assert direct['text']==old['text'] and direct['text_hash']==old['text_hash'] and json.loads(direct['result'])==result
        cache=d.execute('SELECT * FROM cache WHERE text_hash=? AND config=?',(old['text_hash'],config)).fetchone()
        assert cache is not None and cache['source_id']==origin and json.loads(cache['result'])==result
        matches=[]
        for row in d.execute("SELECT payload FROM calls WHERE role='enrich' AND outcome='succeeded'"):
            call=json.loads(row['payload'])
            if call.get('label_config')!=config or call.get('review_ids')!=[origin]:continue
            check_call(call,frozen,origin,direct['text'])
            raw=json.loads(call['raw_provider_response']['response'])
            if all(raw.get(k)==result[k] for k in ('topic','intent','sentiment','severity','needs_review')):matches.append(call['request_id'])
        assert matches,'No matching successful original source call'
        return {'review_id':rid,'direct_source_id':origin,'original_request_ids':matches,'source_hash_match':True,'same_config_and_result':True,'text_only_original_payload':True,'direct_cache_verified':True}
    finally:d.close()

def audit():
    plan=json.loads((ROOT/'evaluation/frozen/improvement-plan.json').read_text());human=ROOT/'evaluation/human/labels.csv';validation=json.loads((ROOT/'evaluation/human-validation.json').read_text())
    assert hashlib.sha256(human.read_bytes()).hexdigest()==validation['human_file_sha256'],'Human answers changed during evaluation'
    with (ROOT/'evaluation/prediction-input.csv').open(newline='') as f:
        reader=csv.DictReader(f);assert reader.fieldnames==['review_id','review_text','review_rating','review_likes','app_version','review_timestamp'];source={r['review_id']:r for r in reader}
    runs={};total=0
    for name,expected_hash in plan['frozen_configuration_sha256'].items():
        path=ROOT/'evaluation/frozen'/(name+'.json');assert hashlib.sha256(path.read_bytes()).hexdigest()==expected_hash
        frozen=json.loads(path.read_text());root=ROOT/'evaluation/predictions'/name;logs=[json.loads(line) for line in (root/'calls.jsonl').read_text().splitlines() if line.strip()]
        called=set()
        for call in logs:
            rid=call['review_ids'][0];check_call(call,frozen,rid,source[rid]['review_text']);called.add(rid)
        records=[json.loads(line) for line in (root/'records.jsonl').read_text().splitlines() if line.strip()]
        reused=[r for r in records if r['review_id'] not in called]
        run=json.loads((root/'run.json').read_text());assert len(reused)==run['reused_same_config']
        assert not reused or name=='gemma-baseline','Unexpected reuse database; explicit lineage mapping required'
        lineage=[trace_reuse(ROOT/'data/full.sqlite',r,source[r['review_id']],frozen) for r in reused]
        total+=len(logs);runs[name]={'inspected_attempts':len(logs),'payload_fields':['review_text'],'frozen_prompt_match':True,'no_human_answer_fields':True,'reused_records_inspected':len(lineage),'reuse_lineage':lineage}
    code={}
    for filename,expected_hash in plan['frozen_code_sha256'].items():
        current=ROOT/filename;snapshot=ROOT/'evaluation/frozen/core-at-evaluation.py' if filename=='pipeline/core.py' else current
        path=snapshot if snapshot.exists() else current
        assert hashlib.sha256(path.read_bytes()).hexdigest()==expected_hash,'Frozen implementation snapshot changed: '+filename
        code[filename]={'verified_path':str(path.relative_to(ROOT)),'frozen_hash_match':True,'current_matches_frozen':hashlib.sha256(current.read_bytes()).hexdigest()==expected_hash}
    return {'status':'passed','human_file_unchanged':True,'human_file_sha256':validation['human_file_sha256'],'configurations_frozen_before_scoring':'self-attested workflow chronology; not independently timestamp-verified','historical_freeze_timing_independently_verified':False,'frozen_implementation_checks':code,'new_attempts_inspected':total,'reused_predictions_inspected':sum(r['reused_records_inspected'] for r in runs.values()),'runs':runs,'human_answers_sent_to_inference_models':False,'additional_cash_usd':0,'scope':'Saved payload/configuration and direct reuse-lineage audit. Current infrastructure code can differ from preserved frozen snapshot; this audit does not certify the semantic scope of those later edits.'}

if __name__=='__main__':
    report=audit();(ROOT/'evaluation/isolation-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
