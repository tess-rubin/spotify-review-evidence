"""Synthetic validation and lineage fixtures; no human answers."""
import copy,json,sqlite3,tempfile,unittest
from pathlib import Path
from evaluation.evaluate import valid_prediction,expected_configuration
from evaluation.audit_isolation import trace_reuse,canonical_prompt

class PredictionValidation(unittest.TestCase):
 def setUp(self):
  self.record={'review_id':'r','source_sha256':'hash','status':'completed','label_config':'cfg','topic':'other','intent':'praise','severity':1,'sentiment':.5,'entities':[],'evidence_quote':'Good','needs_review':False}
 def valid(self,r):return valid_prediction(r,'Good app','hash','cfg')
 def test_valid(self):self.assertTrue(self.valid(self.record))
 def test_invalid_contract_fields(self):
  for key,value in [('label_config','wrong'),('sentiment',float('nan')),('sentiment',float('inf')),('sentiment',True),('sentiment',2),('entities','name'),('entities',['']),('entities',[4]),('severity',True),('evidence_quote','absent')]:
   with self.subTest(key=key,value=value):self.assertFalse(self.valid({**self.record,key:value}))
 def test_missing_fields(self):
  for key in ('sentiment','entities','needs_review'):
   r=self.record.copy();del r[key];self.assertFalse(self.valid(r))
 def test_frozen_config_resolution(self):
  self.assertEqual(expected_configuration('qwen-v3-paired-policy','unused'),expected_configuration('qwen-v3-rubric-policy','unused'))

class CacheLineage(unittest.TestCase):
 def test_direct_lineage_and_chained_reuse_rejection(self):
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'db.sqlite';d=sqlite3.connect(path)
   d.executescript('CREATE TABLE sources(id TEXT,row_hash TEXT,text TEXT,text_hash TEXT); CREATE TABLE labels(id TEXT,config TEXT,result TEXT,cache_source_id TEXT); CREATE TABLE cache(text_hash TEXT,config TEXT,source_id TEXT,result TEXT); CREATE TABLE calls(role TEXT,outcome TEXT,payload TEXT);')
   result={'topic':'other','intent':'praise','sentiment':.5,'severity':1,'needs_review':False,'entities':[],'evidence_quote':'Good'};frozen={'config':{'prompt':'frozen prompt'},'label_config':'cfg'}
   for rid in ('target','origin'):d.execute('INSERT INTO sources VALUES(?,?,?,?)',(rid,'hash','Good','text-hash'))
   d.execute('INSERT INTO labels VALUES(?,?,?,?)',('target','cfg',json.dumps(result),'origin'));d.execute('INSERT INTO labels VALUES(?,?,?,NULL)',('origin','cfg',json.dumps(result)));d.execute('INSERT INTO cache VALUES(?,?,?,?)',('text-hash','cfg','origin',json.dumps(result)))
   call={'request_id':'request','role':'enrich','review_ids':['origin'],'input':{'review_text':'Good'},'actual_prompt':canonical_prompt(frozen),'label_config':'cfg','settings':frozen['config'],'raw_provider_response':{'response':json.dumps({k:result[k] for k in ('topic','intent','sentiment','severity','needs_review')})}}
   d.execute('INSERT INTO calls VALUES(?,?,?)',('enrich','succeeded',json.dumps(call)));d.commit()
   record={'review_id':'target','source_sha256':'hash',**result};source={'review_text':'Good'}
   self.assertEqual(trace_reuse(path,record,source,frozen)['direct_source_id'],'origin')
   d.execute("UPDATE labels SET cache_source_id='another' WHERE id='origin'");d.commit()
   with self.assertRaises(AssertionError):trace_reuse(path,record,source,frozen)
   d.close()
