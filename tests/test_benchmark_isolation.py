"""Checks saved development sampling, without opening human-answer files."""
import csv,hashlib,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'experiments/faster-classifier'
class BenchmarkIsolation(unittest.TestCase):
 def test_text_and_id_disjoint(self):
  rows=list(csv.DictReader((OUT/'development_100.csv').open()));self.assertEqual(len(rows),100)
  ids={r['review_id'] for r in rows};texts={r['review_text'] for r in rows};self.assertEqual(len(texts),100)
  for filename in ('golden_50_to_label.csv','cost_100.csv','checkpoint_500.csv'):
   excluded=list(csv.DictReader((ROOT/'supplied'/filename).open()));self.assertFalse(ids&{r['review_id'] for r in excluded});self.assertFalse(texts&{r['review_text'] for r in excluded})
 def test_only_model_changed(self):
  a=json.loads((OUT/'reference-profile.json').read_text())['config'];b=json.loads((OUT/'candidate-profile.json').read_text())['config'];self.assertEqual({k for k in a if a[k]!=b[k]},{'model','model_digest'})
 def test_frozen_files_unchanged(self):
  frozen=json.loads((OUT/'freeze.json').read_text())
  for filename,expected in frozen['files_sha256'].items():self.assertEqual(hashlib.sha256((OUT/filename).read_bytes()).hexdigest(),expected)
 def test_projection_volume_preserves_measurements(self):
  from cost.faster_benchmark import calculate
  if not (OUT/'candidate-warm-measurement.json').exists():self.skipTest('Benchmark execution still pending')
  a=calculate();b=calculate(10000);self.assertEqual(a['models'],b['models']);self.assertEqual(a['real_development_reference_agreement'],b['real_development_reference_agreement']);self.assertNotEqual(a['scenarios'][0]['total_hours'],b['scenarios'][0]['total_hours'])
