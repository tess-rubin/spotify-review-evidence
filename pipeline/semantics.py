"""Rubric-only consistency policy; no review IDs, texts or human answers used."""
from copy import deepcopy
POLICY_ID='complaint-minimum-severity-two-flag-review-v1'
def apply_policy(result):
    output=deepcopy(result);changes=[]
    for review_id,label in output.items():
        if label['intent']=='complaint' and label['severity']==1:
            label['severity']=2
            label['needs_review']=True
            changes.append({'review_id':review_id,'rule':POLICY_ID,'field':'severity','before':1,'after':2,'needs_review':True})
    return output,changes
