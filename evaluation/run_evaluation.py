"""Score frozen predictions after their completion. No model access, no tuning."""
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from evaluation.evaluate import evaluate,write
ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    plan=json.loads((ROOT/'evaluation/frozen/improvement-plan.json').read_text());reports={}
    for name,expected in plan['frozen_configuration_sha256'].items():
        path=ROOT/'evaluation/frozen'/(name+'.json')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError('Frozen configuration changed after lock')
        records=ROOT/'evaluation/predictions'/name/'records.jsonl'
        if not records.exists():raise ValueError('Predictions not yet complete: '+name)
        run=json.loads((records.parent/'run.json').read_text())
        if run['completed']!=50:raise ValueError('Not all golden predictions saved')
    for filename,expected in plan['frozen_code_sha256'].items():
        snapshot=ROOT/'evaluation/frozen/core-at-evaluation.py' if filename=='pipeline/core.py' else ROOT/filename
        if hashlib.sha256(snapshot.read_bytes()).hexdigest()!=expected:raise ValueError('Frozen classifier implementation snapshot changed')
    # This is the first scoring/inspection of human answer values for this round.
    for name in plan['frozen_configuration_sha256']:
        report,_=evaluate(ROOT/'evaluation/human/labels.csv',records=ROOT/'evaluation/predictions'/name/'records.jsonl',name=name)
        reports[name]=report
    # Paired, deterministic policy effect: evaluate a derivative of identical saved raw predictions.
    from pipeline.semantics import apply_policy
    base=ROOT/'evaluation/predictions/qwen-v2-frozen/records.jsonl';records=[json.loads(line) for line in base.read_text().splitlines() if line.strip()]
    candidate=json.loads((ROOT/'evaluation/frozen/qwen-v3-rubric-policy.json').read_text());changes=[];derived=[]
    for record in records:
        result,change=apply_policy({record['review_id']:{k:record[k] for k in ('topic','intent','sentiment','severity','entities','evidence_quote','needs_review')}})
        derived.append({**record,**result[record['review_id']],'label_config':candidate['label_config'],'evaluation_only_derivative':True,'raw_predictions_source':str(base)})
        changes.extend(change)
    path=ROOT/'evaluation/predictions/qwen-v3-paired-policy/records.jsonl';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in derived))
    write(path.parent/'derivation.json',{'new_model_calls':0,'not_provider_call_evidence':True,'source_sha256':hashlib.sha256(base.read_bytes()).hexdigest(),'policy':candidate['config']['postprocessing_policy'],'changes':changes})
    report,_=evaluate(ROOT/'evaluation/human/labels.csv',records=path,name='qwen-v3-paired-policy');reports['qwen-v3-paired-policy']=report
    write(ROOT/'evaluation/summary.json',{'status':'scored','human_answers_used_for_tuning':False,'candidate_frozen_before_error_inspection':True,'reports':reports})
    write(ROOT/'evaluation/report.json',reports['qwen-v3-rubric-policy'])
    print(json.dumps({name:{k:r[k] for k in ('completed_predictions','accuracy','macro_f1','severity_mae_completed','all_three_correct','needs_review_count','error_counts')} for name,r in reports.items()},indent=2))
