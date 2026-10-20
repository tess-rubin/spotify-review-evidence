"""Validate protected human answers without exposing them to model code."""
import csv,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'supplied'))
from check_submission import FIELDS,TOPICS,INTENTS,row_sha
ROOT=Path(__file__).resolve().parents[1]
def validate(path):
    with open(ROOT/'supplied/golden_50_to_label.csv',newline='',encoding='utf-8-sig') as f:source=list(csv.DictReader(f))
    with open(path,newline='',encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
    expected={r['review_id']:r for r in source};ids=[r.get('review_id') for r in rows];errors=[];metadata_warnings=[]
    if len(rows)!=50 or len(set(ids))!=50 or set(ids)!=set(expected):errors.append({'code':'golden_ids_mismatch','count':len(rows)})
    topic='human_topic' if rows and 'human_topic' in rows[0] else 'topic';intent='human_intent' if rows and 'human_intent' in rows[0] else 'intent';severity='human_severity' if rows and 'human_severity' in rows[0] else 'severity'
    for r in rows:
        rid=r.get('review_id')
        if rid not in expected:continue
        if r.get('review_text')!=expected[rid]['review_text']:errors.append({'code':'source_text_changed','review_id':rid})
        for key in FIELDS[2:]:
            if r.get(key)!=expected[rid][key]:metadata_warnings.append({'code':'human_sheet_metadata_representation_changed','review_id':rid,'field':key,'action':'retain human sheet unchanged; use canonical supplied source for inference and hashes'})
        for key,allowed in ((topic,TOPICS),(intent,INTENTS),(severity,('1','2','3','4','5'))):
            if r.get(key,'') not in allowed:errors.append({'code':'invalid_or_missing_label','review_id':rid,'field':key})
    report={'status':'valid' if not errors else 'invalid','human_answer_rows':len(rows),'valid_human_answers':len(rows)-len({e.get('review_id') for e in errors if e.get('review_id')}),'human_file_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),'errors':errors,'metadata_warnings':metadata_warnings,'source_ids_match':len(rows)==50 and len(set(ids))==50 and set(ids)==set(expected),'source_fields':list(FIELDS),'label_fields':{'topic':topic,'intent':intent,'severity':severity}}
    return report,rows,expected
if __name__=='__main__':
    report,_,source=validate(ROOT/'evaluation/human/labels.csv');(ROOT/'evaluation/human-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='metadata_warnings'},indent=2));print('Metadata presentation warnings:',len(report['metadata_warnings']))
    if report['status']!='valid':raise SystemExit(1)
    # Only this source-only file may be ingested by prediction workers.
    with open(ROOT/'evaluation/prediction-input.csv','w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows({k:r[k] for k in FIELDS} for r in source.values())
