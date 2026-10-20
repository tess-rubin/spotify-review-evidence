"""Synthetic reliability regressions. No inference or held-out labels."""
import copy,csv,hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from pipeline import core as c

class ReliabilityAudit(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.db=self.root/'test.sqlite'
 def tearDown(self):self.tmp.cleanup()
 def write_csv(self,ids):
  path=self.root/'source.csv'
  with path.open('w',newline='') as f:
   fields=['review_id','review_text','review_rating','review_likes','app_version','review_timestamp'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
   for rid in ids:w.writerow(dict(zip(fields,[rid,'Synthetic '+rid,'5','0','test','2026-01-01'])))
  return path
 def test_prefix_extension_and_identical_replay(self):
  c.ingest(self.write_csv(['a']),self.db);c.ingest(self.write_csv(['a','b']),self.db);c.ingest(self.write_csv(['a','b']),self.db)
  with c.dbopen(self.db) as d:self.assertEqual(d.execute('SELECT count(*) FROM sources').fetchone()[0],2)
 def test_ordinal_conflict_rolls_back_whole_ingest(self):
  c.ingest(self.write_csv(['a']),self.db)
  with self.assertRaises(ValueError):c.ingest(self.write_csv(['alien','b']),self.db)
  with c.dbopen(self.db) as d:self.assertEqual([r[0] for r in d.execute('SELECT id FROM sources')],['a'])
 def test_shorter_input_and_partial_extension_rollback(self):
  c.ingest(self.write_csv(['a']),self.db)
  with self.assertRaises(ValueError):c.ingest(self.write_csv(['a','b','a']),self.db)
  with c.dbopen(self.db) as d:self.assertEqual(d.execute('SELECT count(*) FROM sources').fetchone()[0],1)
  c.ingest(self.write_csv(['a','b']),self.db)
  with self.assertRaises(ValueError):c.ingest(self.write_csv(['a']),self.db)
 def test_reordering_rejected(self):
  c.ingest(self.write_csv(['a','b']),self.db)
  with self.assertRaises(ValueError):c.ingest(self.write_csv(['b','a']),self.db)
 def saved_call(self,mutate=None,legacy=False):
  path=self.write_csv(['a']);c.ingest(path,self.db);d=c.dbopen(self.db)
  result={'topic':'other','intent':'praise','sentiment':1,'severity':1,'entities':[],'evidence_quote':'Synthetic a','needs_review':False}
  answer={k:v for k,v in result.items() if k not in ('entities','evidence_quote')}
  raw={'message':{'content':json.dumps(answer)}} if c.CONFIG.get('api')=='chat' else {'response':json.dumps(answer)}
  log={'label_config':c.LABEL_CONFIG,'settings':copy.deepcopy(c.CONFIG),'review_ids':['a'],'input':{'review_text':'Synthetic a'},'raw_provider_response':raw}
  if not legacy:log['validated_result']={'a':result}
  if mutate:mutate(log)
  with d:d.execute('INSERT INTO calls VALUES(?,?,?,?,?,?)',('saved-request','previous-run','enrich','initial','succeeded',json.dumps(log)))
  return d,path
 def test_saved_success_recovered_without_call(self):
  d,path=self.saved_call();d.close()
  with patch.object(c,'modelcall',side_effect=AssertionError('No new inference')),patch.object(c,'ROOT',self.root):
   report=c.execute(self.db,path,4.9,stop_after=1)
  self.assertEqual(report['recovered_successful_results'],1);self.assertEqual(report['completed'],1)
  with c.dbopen(self.db) as d:
   self.assertIsNone(d.execute('SELECT cache_source_id FROM labels').fetchone()[0]);self.assertEqual(d.execute('SELECT source_id FROM cache').fetchone()[0],'a')
 def test_legacy_success_recovered_from_raw(self):
  d,_=self.saved_call(legacy=True);self.assertEqual(c.recover_successful_enrichment(d),1);self.assertEqual(c.recover_successful_enrichment(d),0);d.close()
 def test_wrong_config_text_ids_or_evidence_never_recovered(self):
  mutations=[lambda x:x.update(label_config='wrong'),lambda x:x['settings'].update(seed=999),lambda x:x['input'].update(review_text='alien'),lambda x:x.update(review_ids=['alien']),lambda x:x['validated_result']['a'].update(evidence_quote='fabricated')]
  for mutate in mutations:
   with self.subTest(mutation=mutate):
    d,_=self.saved_call(mutate);self.assertEqual(c.recover_successful_enrichment(d),0)
    with d:d.execute('DELETE FROM calls')
    d.close()
 def test_recovery_alias_points_directly_to_original(self):
  d,_=self.saved_call()
  self.assertEqual(c.recover_successful_enrichment(d),1)
  with d:
   row=d.execute('SELECT * FROM sources WHERE id="a"').fetchone();d.execute('INSERT INTO sources VALUES(?,?,?,?,?,?,?,?)',('b',1,'{}','different-row',row['text'],row['text_hash'],'pending',None))
   saved=json.loads(d.execute('SELECT payload FROM calls').fetchone()[0]);saved['review_ids']=['b'];saved['validated_result']={'b':saved['validated_result']['a']};d.execute('INSERT INTO calls VALUES(?,?,?,?,?,?)',('second','previous-run','enrich','initial','succeeded',json.dumps(saved)))
  self.assertEqual(c.recover_successful_enrichment(d),1)
  self.assertEqual(d.execute('SELECT cache_source_id FROM labels WHERE id="b"').fetchone()[0],'a');d.close()

class InterruptedAccounting(unittest.TestCase):
 setUp=ReliabilityAudit.setUp
 tearDown=ReliabilityAudit.tearDown
 write_csv=ReliabilityAudit.write_csv
 def test_orphan_attempt_and_run_reconciled(self):
  d=c.dbopen(self.db)
  with d:
   d.execute('INSERT INTO calls VALUES(?,?,?,?,?,?)',('orphan','old','enrich','initial','in_flight',json.dumps({'request_id':'orphan','run_id':'old'})))
   d.execute('INSERT INTO ledger VALUES(?,?,?,?)',('orphan',0,0,'reserved'))
   d.execute('INSERT INTO runs VALUES(?,?)',('old',json.dumps({'status':'running'})))
  c.reconcile_interrupted(d)
  self.assertEqual(d.execute('SELECT outcome FROM calls').fetchone()[0],'interrupted')
  self.assertEqual(json.loads(d.execute('SELECT payload FROM runs').fetchone()[0])['status'],'interrupted');d.close()
 def test_keyboard_interrupt_records_terminal_run_and_releases_lease(self):
  path=self.write_csv(['a']);c.ingest(path,self.db)
  with patch.object(c,'modelcall',side_effect=KeyboardInterrupt),patch.object(c,'ROOT',self.root):
   with self.assertRaises(KeyboardInterrupt):c.execute(self.db,path,4.9,stop_after=1)
  with c.dbopen(self.db) as d:
   self.assertEqual(json.loads(d.execute('SELECT payload FROM runs').fetchone()[0])['status'],'interrupted')
   self.assertEqual(d.execute('SELECT count(*) FROM leases').fetchone()[0],0)

if __name__=='__main__':unittest.main()
