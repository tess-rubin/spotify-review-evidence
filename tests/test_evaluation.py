"""Synthetic scorer tests; never use real human answers as test fixtures."""
import unittest
from evaluation.evaluate import metrics
from pipeline.core import TOPICS,INTENTS
class Scorer(unittest.TestCase):
 def test_missing_predictions_stay_in_accuracy_denominator(self):
  pairs=[({'topic':'other'},{'topic':'other'}),({'topic':'billing'},{}),({'topic':'other'},{'topic':'playback'})]
  result=metrics(pairs,'topic',TOPICS)
  self.assertEqual(result['accuracy'],1/3)
  self.assertEqual(result['confusion']['billing']['__missing__'],1)
  self.assertEqual(result['per_label']['other']['false_negative'],1)
 def test_precision_recall_and_absent_classes(self):
  pairs=[({'intent':'praise'},{'intent':'praise'}),({'intent':'complaint'},{'intent':'praise'})]
  result=metrics(pairs,'intent',INTENTS)
  self.assertEqual(result['per_label']['praise']['precision'],.5)
  self.assertEqual(result['per_label']['praise']['recall'],1)
  self.assertAlmostEqual(result['macro_f1'],(2/3)/len(INTENTS))
  self.assertAlmostEqual(result['macro_f1_supported_labels'],1/3)

class FrozenProfile(unittest.TestCase):
 def test_runnable_profile_matches_frozen_candidate(self):
  import json,hashlib
  from pathlib import Path
  root=Path(__file__).resolve().parents[1]
  profile=json.loads((root/'pipeline/configs/qwen-v3.json').read_text())
  frozen=json.loads((root/'evaluation/frozen/qwen-v3-rubric-policy.json').read_text())
  self.assertEqual(profile,frozen)
  self.assertEqual(profile['label_config'],hashlib.sha256(json.dumps(profile['config'],sort_keys=True).encode()).hexdigest())
  self.assertIn('postprocessing_policy',profile['config'])

class HumanInputGuard(unittest.TestCase):
 def test_runner_rejects_human_answer_file_before_inference(self):
  import subprocess,sys
  from pathlib import Path
  root=Path(__file__).resolve().parents[1]
  result=subprocess.run([sys.executable,str(root/'pipeline/run.py'),str(root/'evaluation/human/labels.csv'),'--execute-local','--spend-cap','4.90'],capture_output=True,text=True,cwd=root)
  self.assertNotEqual(result.returncode,0)
  self.assertIn('Protected human-answer files',result.stderr)
