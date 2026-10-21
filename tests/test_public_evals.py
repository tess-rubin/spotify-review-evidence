import subprocess,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class PublicEvaluationIsolation(unittest.TestCase):
 def test_saved_evidence_consistent(self):
  result=subprocess.run([sys.executable,str(ROOT/'evals/check_saved.py')],capture_output=True,text=True)
  self.assertEqual(result.returncode,0,result.stderr)
 def test_classifier_rejects_public_evaluation_files(self):
  result=subprocess.run([sys.executable,str(ROOT/'pipeline/hosted_csv.py'),str(ROOT/'evals/expected.json')],capture_output=True,text=True)
  self.assertNotEqual(result.returncode,0)
  self.assertIn('must never be used as model input',result.stderr)
if __name__=='__main__':unittest.main()
