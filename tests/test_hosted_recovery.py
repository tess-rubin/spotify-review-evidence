"""Synthetic offline hosted recovery regressions; never access live state or keys."""
import copy,csv,hashlib,json,tempfile,unittest
from contextlib import ExitStack,closing
from pathlib import Path
from unittest.mock import patch
from pipeline import core as c, hosted as h, hosted_finish as f

class HostedRecovery(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);(self.root/'supplied').mkdir();self.state=self.root/'data/hosted';self.state.mkdir(parents=True)
  self.stack=ExitStack();self.old_config=copy.deepcopy(c.CONFIG);self.old_label=c.LABEL_CONFIG
  for obj,name,value in [(h,'ROOT',self.root),(h,'STATE',self.state),(h,'LEDGER',self.root/'ledger.sqlite'),(f,'ROOT',self.root)]:self.stack.enter_context(patch.object(obj,name,value))
  self.stack.enter_context(patch.object(h,'credentials',side_effect=AssertionError('No credentials permitted')))
  self.stack.enter_context(patch.object(h.urllib.request,'urlopen',side_effect=AssertionError('No network permitted')))
 def tearDown(self):
  self.stack.close();c.CONFIG.clear();c.CONFIG.update(self.old_config);c.LABEL_CONFIG=self.old_label;self.temp.cleanup()
 def canonical(self,count=100):
  path=self.root/'supplied/cost_100.csv';fields=['review_id','review_text','review_rating','review_likes','app_version','review_timestamp']
  with path.open('w',newline='') as stream:
   writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
   for i in range(count):writer.writerow(dict(zip(fields,[str(i),'Synthetic review '+str(i),'3','0','synthetic','2026-01-01'])))
  return path
 def test_atomic_initialization_and_validated_resume(self):
  source=self.canonical();path=h.initialize('pilot');self.assertTrue(path.is_file());self.assertFalse(path.with_name('pilot.initializing.sqlite').exists())
  with closing(c.dbopen(path)) as d:
   self.assertEqual(d.execute('SELECT count(*) FROM sources').fetchone()[0],100)
   identity=json.loads(d.execute("SELECT value FROM artifacts WHERE key='hosted-source-identity'").fetchone()[0]);self.assertEqual(identity,{'rows':100,'input_sha256':c.sha(source)})
  self.assertEqual(h.initialize('pilot'),path)
 def test_existing_empty_db_refused(self):
  self.canonical();c.dbopen(self.state/'pilot.sqlite').close()
  with self.assertRaisesRegex(RuntimeError,'SOURCE_SCOPE_MISMATCH'):h.initialize('pilot')
 def test_changed_source_identity_refused(self):
  source=self.canonical();h.initialize('pilot');source.write_text(source.read_text()+'\n')
  with self.assertRaisesRegex(RuntimeError,'Source identity changed'):h.initialize('pilot')
 def test_interrupted_temp_is_never_published_and_can_restart(self):
  self.canonical()
  def interrupt(input_path,db):c.dbopen(db).close();raise KeyboardInterrupt
  with patch.object(c,'ingest',side_effect=interrupt):
   with self.assertRaises(KeyboardInterrupt):h.initialize('pilot')
  self.assertFalse((self.state/'pilot.sqlite').exists());self.assertTrue((self.state/'pilot.initializing.sqlite').exists())
  self.assertTrue(h.initialize('pilot').exists())
 def test_partial_selection_requires_full_target(self):
  d=c.dbopen(self.state/'tiny.sqlite')
  with patch.object(c,'csv_rows',return_value=[]):
   with self.assertRaisesRegex(RuntimeError,'exactly 100000'):h.selected_rows(d,'partial')
  d.close()
 def test_reservation_breach_commits_usage_and_blocks_next_dispatch(self):
  h.reserve('synthetic-underestimate','enrich',10)
  usage={'prompt_tokens':1000,'completion_tokens':1000}
  with self.assertRaisesRegex(RuntimeError,'ledger blocked'):h.settle('synthetic-underestimate',usage)
  with closing(h.ledger()) as d:
   row=d.execute('SELECT * FROM spend').fetchone();self.assertEqual(row['actual'],600);self.assertEqual(row['reserved'],0);self.assertEqual(row['state'],'reservation_breached');self.assertEqual(json.loads(row['usage']),usage)
  with self.assertRaisesRegex(RuntimeError,'LEDGER_BLOCKED'):h.reserve('another','verify',1)
 def downstream_fixture(self,artifact_keys=False,wrong_settings=False,bad_quote=False):
  d=c.dbopen(self.state/'pilot.sqlite');text='Synthetic playback failure';th=hashlib.sha256(text.encode()).hexdigest()
  pred={'topic':'playback','intent':'complaint','severity':3,'sentiment':-.5,'needs_review':False,'entities':[],'evidence_quote':text}
  with d:
   d.execute('INSERT INTO sources VALUES(?,?,?,?,?,?,?,?)',('synthetic-id',0,'{}','synthetic-row-hash',text,th,'pending',None));d.execute('INSERT INTO labels VALUES(?,?,?,NULL)',('synthetic-id',h.LABEL_CONFIG,json.dumps(pred)))
  packs=h.aggregate(d);row=d.execute('SELECT * FROM sources').fetchone()
  for role in ('verify','memo'):
   selected=[row] if role=='verify' else [];payload=None if role=='verify' else {'issues':packs};prompt='Independently classify, blind to any prior predictions. '+h.PROMPT if role=='verify' else h.MEMO_PROMPT
   result={'synthetic-id':pred} if role=='verify' else {'recommendations':[{'issue_id':'issue-playback','review_id':'synthetic-id','quote':text,'action':'Investigate playback failures'}]}
   if bad_quote and role=='verify':result={'synthetic-id':dict(pred,evidence_quote='invented')}
   identity={'role':role,'role_version':'hosted-finish-v1','prompt':prompt,'label_config':h.LABEL_CONFIG,'rows':[{k:r[k] for k in ('id','text_hash')} for r in selected],'payload':payload}
   key='hosted-finish-'+hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
   log={'label_config':h.LABEL_CONFIG,'settings':dict(h.CONFIG),'input':payload if payload is not None else {'reviews':{'r0':text}},'review_ids':[r['id'] for r in selected],'request_body':{'messages':[{'content':prompt}]},'validated_result':result}
   if wrong_settings:log['settings']['model']='synthetic-wrong-model'
   if artifact_keys:log['artifact_key']=key;log.pop('input');log.pop('request_body')
   with d:d.execute('INSERT INTO calls VALUES(?,?,?,?,?,?)',('saved-'+role,'interrupted-run',role,'initial','succeeded',json.dumps(log)))
  d.close()
 def finish_without_dispatch(self):
  with patch.object(h,'credentials',return_value='synthetic-not-a-key'),patch.object(h,'acquire'),patch.object(h,'release'),patch.object(h,'budget_status',return_value={'spent_usd':0}),patch.object(h,'request',side_effect=AssertionError('Unexpected paid dispatch')):
   return f.finish('pilot')
 def test_legacy_downstream_success_recovers_and_warm_reuses(self):
  self.downstream_fixture();first=self.finish_without_dispatch();second=self.finish_without_dispatch()
  self.assertEqual(first['new_calls'],{'verify':0,'memo':0});self.assertEqual(second['new_calls'],{'verify':0,'memo':0})
  with closing(c.dbopen(self.state/'pilot.sqlite')) as d:self.assertEqual(d.execute('SELECT count(*) FROM artifacts').fetchone()[0],2)
 def test_keyed_downstream_success_recovers(self):
  self.downstream_fixture(artifact_keys=True);self.assertEqual(self.finish_without_dispatch()['new_calls'],{'verify':0,'memo':0})
 def test_wrong_configuration_never_recovered(self):
  self.downstream_fixture(wrong_settings=True)
  with self.assertRaisesRegex(AssertionError,'Unexpected paid dispatch'):self.finish_without_dispatch()
 def test_recovered_quote_is_revalidated(self):
  self.downstream_fixture(bad_quote=True)
  with self.assertRaisesRegex(ValueError,'Unsupported quote'):self.finish_without_dispatch()

if __name__=='__main__':unittest.main()
