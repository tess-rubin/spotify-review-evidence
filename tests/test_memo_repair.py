import unittest
from pipeline import hosted as h
class MemoRepair(unittest.TestCase):
 def setUp(self):self.extra={'issues':[{'issue_id':'issue-catalog','evidence':[{'review_id':'exact-original','quote':'Lyrics missing on Galaxy M51.'}]}]}
 def test_code_binds_exact_citation_and_device_identifier(self):
  r=h.normalize_memo({'recommendations':[{'issue_id':'issue-catalog','evidence_ref':'e0','action':'Investigate lyrics support on Galaxy M51.'}]},self.extra)
  self.assertEqual(r['recommendations'][0]['review_id'],'exact-original');self.assertEqual(r['recommendations'][0]['quote'],'Lyrics missing on Galaxy M51.')
 def test_unknown_reference_and_duplicate_issue_rejected(self):
  item={'issue_id':'issue-catalog','evidence_ref':'e1','action':'Investigate lyrics support.'}
  with self.assertRaises(ValueError):h.normalize_memo({'recommendations':[item]},self.extra)
  item['evidence_ref']='e0'
  with self.assertRaises(ValueError):h.normalize_memo({'recommendations':[item,item]},self.extra)
 def test_unsupported_metrics_and_device_identifiers_rejected(self):
  for action in ('Improve 50 percent of errors.','Reduce errors by half.','Investigate Galaxy M99.'):
   self.assertFalse(h.valid_action(action,'Lyrics missing on Galaxy M51.'))
