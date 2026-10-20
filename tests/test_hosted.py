import json,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from pipeline import hosted as h
class HostedControls(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.old=h.LEDGER;h.LEDGER=Path(self.temp.name)/'spend.sqlite';self.cap=h.CAP;h.CAP=10000
  self.rows=[{'id':'original-1','text':'Nice music','text_hash':'h1'},{'id':'original-2','text':'Cannot log in','text_hash':'h2'}]
  self.answer={'results':[{'id':'r0','t':'other','i':'praise','s':1,'p':.8,'n':False},{'id':'r1','t':'access','i':'complaint','s':4,'p':-.8,'n':False}]}
 def tearDown(self):h.LEDGER=self.old;h.CAP=self.cap;self.temp.cleanup()
 def test_cumulative_reservations_reject_before_dispatch(self):
  h.reserve('one','enrich',6000)
  with self.assertRaisesRegex(RuntimeError,'HARD_SPEND_CAP'):h.reserve('two','enrich',4001)
  self.assertEqual(h.budget_status()['reserved_or_unknown_usd'],.006)
 def test_settlement_and_retry_reservation(self):
  h.reserve('one','enrich',6000);h.settle('one',{'prompt_tokens':1000,'completion_tokens':1000});h.reserve('retry','enrich',9000)
  with self.assertRaises(RuntimeError):h.reserve('three','memo',1000)
 def test_unknown_charge_stays_reserved(self):
  h.reserve('one','enrich',9000);h.settle('one');self.assertEqual(h.budget_status()['reserved_or_unknown_usd'],.009)
  with self.assertRaises(RuntimeError):h.reserve('retry','enrich',1001)
 def test_ids_and_full_quote(self):
  results=h.validate(self.answer,self.rows);self.assertEqual(set(results),{'original-1','original-2'});self.assertEqual(results['original-1']['evidence_quote'],'Nice music');self.assertEqual(results['original-2']['entities'],[])
 def test_missing_duplicate_unknown_ids(self):
  for ids in (['r0'],['r0','r0'],['r0','r9']):
   answer={'results':[dict(self.answer['results'][min(i,1)],id=rid) for i,rid in enumerate(ids)]}
   with self.assertRaises(ValueError):h.validate(answer,self.rows)
 def test_nonfinite_sentiment_rejected(self):
  self.answer['results'][0]['p']=float('nan')
  with self.assertRaises(ValueError):h.validate(self.answer,self.rows)
 def test_shared_worker_lease(self):
  h.acquire()
  with self.assertRaises(RuntimeError):h.acquire()
  h.release();h.acquire();h.release()
 def test_rejected_request_releases_reservation(self):
  h.reserve('one','enrich',9000);h.settle('one',rejected=True);self.assertEqual(h.budget_status()['reserved_or_unknown_usd'],0)
if __name__=='__main__':unittest.main()

class HostedCalculator(unittest.TestCase):
 def test_rates_and_volume_preserve_recorded_usage(self):
  from cost.hosted_calculator import calculate
  a=calculate();b=calculate(multiplier=2);v=calculate(volume=200000)
  self.assertEqual(a['recorded_pilot_measurements'],b['recorded_pilot_measurements']);self.assertEqual(a['recorded_pilot_measurements'],v['recorded_pilot_measurements'])
  self.assertAlmostEqual(b['conservative_100000_total_usd'],a['conservative_100000_total_usd']*2)
  self.assertAlmostEqual(b['roles']['enrich']['api_usd'],a['roles']['enrich']['api_usd']*2)

class HostedOverflow(unittest.TestCase):
 setUp=HostedControls.setUp
 tearDown=HostedControls.tearDown
 def test_overflow_persists_usage_and_blocks_dispatch(self):
  h.reserve('overflow','enrich',10)
  with self.assertRaises(RuntimeError):h.settle('overflow',{'prompt_tokens':1000,'completion_tokens':1000})
  self.assertEqual(h.budget_status()['spent_usd'],.0006)
  with self.assertRaisesRegex(RuntimeError,'LEDGER_BLOCKED'):h.reserve('future','enrich',10)
