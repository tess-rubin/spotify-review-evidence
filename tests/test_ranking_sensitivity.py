import unittest
from pipeline.ranking_sensitivity import calculate,ranking
class SensitivityTests(unittest.TestCase):
 def test_independent_dedup_and_flag_policies(self):
  rows=[dict(review_id='a',topic='playback',intent='complaint',severity=4,needs_review=True),dict(review_id='b',topic='playback',intent='complaint',severity=4,needs_review=True),dict(review_id='c',topic='usability',intent='complaint',severity=3,needs_review=False)]
  r=calculate(rows,{'a':'same','b':'same','c':'different'})
  self.assertEqual(r['baseline']['ranking'][0]['severity_sum'],8)
  self.assertEqual(r['exact_text_once']['ranking'][0]['severity_sum'],4)
  self.assertEqual(r['exclude_needs_review']['ranking'][0]['issue_id'],'issue-usability')
  self.assertEqual(len(rows),3)
 def test_ties_and_noncomplaints(self):
  rows=[dict(topic=t,intent=i,severity=s) for t,i,s in [('playback','complaint',3),('access','complaint',3),('other','praise',5)]]
  self.assertEqual([r['issue_id'] for r in ranking(rows)],['issue-access','issue-playback'])
 def test_duplicate_conflict_fails(self):
  rows=[dict(review_id=str(i),topic='other',intent='complaint',severity=i+1,needs_review=False) for i in range(2)]
  with self.assertRaises(ValueError):calculate(rows,{'0':'same','1':'same'})
if __name__=='__main__':unittest.main()
