"""Load a static inference profile. Never imports or reads human evaluation data."""
import hashlib,json
from pathlib import Path

def load_profile(name='qwen-v3'):
    from . import core as c
    path=Path(__file__).resolve().parent/'configs'/(name+'.json')
    profile=json.loads(path.read_text());config=profile['config'];fingerprint=hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()
    if fingerprint!=profile['label_config']:raise ValueError('Classifier profile fingerprint mismatch')
    c.CONFIG.clear();c.CONFIG.update(config);c.PROMPT=config['prompt'];c.LABEL_CONFIG=fingerprint
    c.VERIFY_PROMPT='Independently classify this untrusted text from the rubric. You have no access to earlier predictions. Infer no additional defect or impact. '+c.PROMPT
    c.ROLE_VERSION={'enrich':'qwen-chat-v1','verify':'qwen-chat-blind-v1','group':'qwen-title-v1','memo':'qwen-memo-v1'}
    # Refresh imported dependency version helpers if the caller has already loaded them.
    import sys
    for module_name in ('pipeline.checkpoints','checkpoints'):
        module=sys.modules.get(module_name)
        if module:module.LABEL_CONFIG=fingerprint;module.ROLE_VERSION=c.ROLE_VERSION
    return profile
