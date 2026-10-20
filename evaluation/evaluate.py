"""Offline scoring only. Never sends human answers to a model or changes a classifier."""
import argparse,csv,gzip,hashlib,json,math,sqlite3,sys
from collections import Counter
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pipeline.core import LABEL_CONFIG,TOPICS,INTENTS,FIELDS as LABEL_FIELDS
from evaluation.validate_labels import validate,ROOT
sys.path.insert(0,str(ROOT/'supplied'))
from check_submission import row_sha

def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def expected_configuration(name,config):
    profile_name='qwen-v3-rubric-policy' if name=='qwen-v3-paired-policy' else name
    profile=ROOT/'evaluation/frozen'/(profile_name+'.json')
    return json.loads(profile.read_text())['label_config'] if profile.exists() else config

def valid_prediction(pred,text,source_hash,expected_config):
    """Validate contract fields independently of inference code and human answers."""
    return (pred.get('status')=='completed' and pred.get('source_sha256')==source_hash
        and pred.get('label_config')==expected_config
        and all(field in pred for field in LABEL_FIELDS)
        and pred.get('topic') in TOPICS and pred.get('intent') in INTENTS
        and type(pred.get('severity')) is int and 1<=pred['severity']<=5
        and type(pred.get('sentiment')) in (float,int) and math.isfinite(pred['sentiment']) and -1<=pred['sentiment']<=1
        and type(pred.get('needs_review')) is bool
        and isinstance(pred.get('entities'),list) and all(isinstance(e,str) and bool(e.strip()) for e in pred['entities'])
        and isinstance(pred.get('evidence_quote'),str) and bool(pred['evidence_quote'].strip()) and pred['evidence_quote'] in text)
def metrics(pairs,field,labels):
    confusion={label:{p:0 for p in [*labels,'__missing__']} for label in labels};per_label={}
    for human,pred in pairs:confusion[human[field]][pred.get(field,'__missing__')]+=1
    for label in labels:
        tp=confusion[label][label];support=sum(confusion[label].values());fp=sum(confusion[h][label] for h in labels if h!=label);fn=support-tp
        precision=tp/(tp+fp) if tp+fp else 0;recall=tp/support if support else 0;f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0
        per_label[label]={'support':support,'precision':precision,'recall':recall,'f1':f1,'true_positive':tp,'false_positive':fp,'false_negative':fn}
    n=len(pairs);supported=[v['f1'] for v in per_label.values() if v['support']]
    return {'accuracy':sum(h[field]==p.get(field) for h,p in pairs)/n,'macro_f1':sum(v['f1'] for v in per_label.values())/len(labels),'macro_f1_supported_labels':sum(supported)/len(supported) if supported else None,'macro_definition':'all contract labels, including labels absent from this sample; absent undefined F1 is 0','per_label':per_label,'confusion':confusion}

def evaluate(labels_path,records=None,db=None,config=LABEL_CONFIG,name='production',out=None):
    validation,humans,source=validate(labels_path)
    if validation['status']!='valid':raise ValueError('Human validation failed; see evaluation/human-validation.json')
    if records:
        path=Path(records);opener=gzip.open if path.name.endswith('.gz') else open
        with opener(path,'rt',encoding='utf-8') as f:rows=[json.loads(line) for line in f if line.strip()]
        predictions={}
        for r in rows:
            if r['review_id'] in predictions:raise ValueError('Duplicate prediction ID')
            predictions[r['review_id']]=r
        identity={'records_path':str(path),'records_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    else:
        conn=sqlite3.connect(db);conn.row_factory=sqlite3.Row;predictions={}
        for r in conn.execute('SELECT l.id,l.config,l.result,s.row_hash FROM labels l JOIN sources s ON s.id=l.id WHERE config=?',(config,)):
            predictions[r['id']]={'review_id':r['id'],'label_config':r['config'],'source_sha256':r['row_hash'],'status':'completed',**json.loads(r['result'])}
        conn.close();identity={'database_path':str(db),'label_config':config}
    expected_config=expected_configuration(name,config)
    keys=validation['label_fields'];comparisons=[];valid_pairs=[];missing=[];invalid=[]
    for r in humans:
        rid=r['review_id'];h={'topic':r[keys['topic']],'intent':r[keys['intent']],'severity':int(r[keys['severity']])};p=predictions.get(rid,{})
        if p:
            valid=valid_prediction(p,source[rid]['review_text'],row_sha(source[rid]),expected_config)
            if not valid:invalid.append(rid);p={}
        else:missing.append(rid)
        errors=[field for field in ('topic','intent','severity') if p.get(field)!=h[field]]
        comparisons.append({'review_id':rid,'source_sha256':row_sha(source[rid]),'review_text':source[rid]['review_text'],'human':h,'prediction':p,'error_fields':errors,'severity_error':abs(h['severity']-p['severity']) if p else None,'descriptive_only_not_for_tuning':True})
        valid_pairs.append((h,p))
    topic=metrics(valid_pairs,'topic',TOPICS);intent=metrics(valid_pairs,'intent',INTENTS);completed=[(h,p) for h,p in valid_pairs if p];n=len(humans)
    optional={}
    for field in ('sentiment','needs_review'):
        pairs=[]
        for human,row in zip(humans,comparisons):
            value=human.get(field,'');pred=row['prediction']
            if not value or not pred:continue
            if field=='sentiment':
                try:value=float(value)
                except ValueError:continue
                if not math.isfinite(value) or not -1<=value<=1:continue
            else:
                if value.lower() not in ('true','false'):continue
                value=value.lower()=='true'
            pairs.append((value,pred[field]))
        if pairs:optional[field]={'human_labeled_count':len(pairs),**({'mae':sum(abs(h-p) for h,p in pairs)/len(pairs)} if field=='sentiment' else {'accuracy':sum(h==p for h,p in pairs)/len(pairs)})}
    entity_pairs=[];entity_invalid=0;quote_human_valid=0;quote_human_present=0
    for human,row in zip(humans,comparisons):
        raw_entities=human.get('entities','');pred=row['prediction']
        if raw_entities and pred:
            try:
                entities=json.loads(raw_entities)
                if not isinstance(entities,list) or not all(isinstance(e,str) for e in entities):raise ValueError()
                entity_pairs.append((set(entities),set(pred.get('entities',[]))))
            except (ValueError,TypeError):entity_invalid+=1
        quote=human.get('evidence_quote','')
        if quote:
            quote_human_present+=1;quote_human_valid+=quote in source[human['review_id']]['review_text']
    if entity_pairs:
        tp=sum(len(h&p) for h,p in entity_pairs);fp=sum(len(p-h) for h,p in entity_pairs);fn=sum(len(h-p) for h,p in entity_pairs)
        optional['entities']={'human_labeled_count':len(entity_pairs),'invalid_human_json_cells':entity_invalid,'set_exact_match':sum(h==p for h,p in entity_pairs)/len(entity_pairs),'micro_f1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 1,'true_positive':tp,'false_positive':fp,'false_negative':fn,'note':'Set equality and micro F1; entity strings remain case-sensitive.'}
    optional['evidence_quote']={'human_nonempty_count':quote_human_present,'human_source_substring_count':quote_human_valid,'valid_prediction_quote_count':len(completed),'note':'Multiple evidence spans can be valid; source anchoring is checked rather than exact equality with a human-selected span.'}
    report={'name':name,'status':'scored','human_answers_used_for':'offline evaluation and descriptive error inspection only','human_file_sha256':validation['human_file_sha256'],'total':n,'valid_human_answers':n,'completed_predictions':len(completed),'missing_predictions':len(missing),'invalid_predictions':len(invalid),'missing_ids':missing,'invalid_ids':invalid,'accuracy':{'topic':topic['accuracy'],'intent':intent['accuracy'],'severity':sum(h['severity']==p.get('severity') for h,p in valid_pairs)/n},'macro_f1':{'topic':topic['macro_f1'],'intent':intent['macro_f1']},'topic':topic,'intent':intent,'severity_mae_completed':sum(abs(h['severity']-p['severity']) for h,p in completed)/len(completed) if completed else None,'severity_mae_all_penalized':sum(abs(h['severity']-p['severity']) if p else 5 for h,p in valid_pairs)/n,'missing_severity_penalty':5,'all_three_correct':sum(not r['error_fields'] for r in comparisons),'all_three_accuracy':sum(not r['error_fields'] for r in comparisons)/n,'needs_review_count':sum(p.get('needs_review',False) for _,p in completed),'error_counts':dict(Counter(f for row in comparisons for f in row['error_fields'])),'optional_fields':optional,'input_identity':identity,'metadata_note':'Human spreadsheet timestamp formatting differs; original source ID/text matches and canonical supplied hashes are used.','limitations':['Only 50 human-labeled reviews; small per-class supports.','Inspection of errors is diagnostic only; frozen candidate was defined before viewing golden results.','Improved scores do not authorize tuning on these human answers or demonstrate full-corpus accuracy.']}
    dest=Path(out or ROOT/'evaluation/results'/name);write(dest/'report.json',report);write(dest/'comparison.json',comparisons)
    for field,data in (('topic',topic),('intent',intent)):
        labels=list(data['confusion']);fields=['human_label',*labels,'__missing__']
        with (dest/(field+'-confusion.csv')).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({'human_label':h,**data['confusion'][h]} for h in labels)
    return report,comparisons

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--labels',default=str(ROOT/'evaluation/human/labels.csv'));p.add_argument('--records');p.add_argument('--db',default=str(ROOT/'data/full.sqlite'));p.add_argument('--config',default=LABEL_CONFIG);p.add_argument('--name',default='production');p.add_argument('--out');a=p.parse_args()
    report,_=evaluate(a.labels,a.records,a.db,a.config,a.name,a.out)
    write(ROOT/'evaluation/report.json',report)
    print(json.dumps({k:report[k] for k in ('name','status','total','completed_predictions','missing_predictions','accuracy','macro_f1','severity_mae_completed','all_three_correct')},indent=2))
