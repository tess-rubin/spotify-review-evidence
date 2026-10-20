import csv
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from pipeline import core
from pipeline.gate import validate_evidence, main
from pipeline.restore import restore


class PipelineAuditTests(unittest.TestCase):
    def test_gate_rejects_profile_mismatch_and_wrong_scope(self):
        prev = {'label_config': 'new', 'status': 'complete', 'input_count': 500, 'remaining': 0}
        quality = {'label_config': 'new', 'cases': [{'injection_resisted': True}]}
        validate_evidence(prev, quality, 'new', 500)
        for bad in [dict(prev, label_config='old'), dict(prev, input_count=100), dict(prev, remaining=1)]:
            with self.assertRaises(ValueError):
                validate_evidence(bad, quality, 'new', 500)
        for bad in [{'label_config': 'old', 'cases': quality['cases']}, {'label_config': 'new', 'cases': []}, {'label_config': 'new', 'cases': [{'injection_resisted': False}]}]:
            with self.assertRaises(ValueError):
                validate_evidence(prev, bad, 'new', 500)

    def test_gate_requires_explicit_profile_and_evidence(self):
        with patch.object(core, 'execute', side_effect=AssertionError('No inference')):
            with self.assertRaises(SystemExit):
                main(['10000', '--spend-cap', '4.9'])

    def test_restore_preserves_nondefault_config_and_rejects_mixed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'source.csv'
            fields = ['review_id', 'review_text', 'review_rating', 'review_likes', 'app_version', 'review_timestamp']
            source_row = dict(zip(fields, ['r1', 'Cannot play music', '1', '0', '', '2023-01-01']))
            with source.open('w', newline='') as handle:
                writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerow(source_row)
            result = {'review_id': 'r1', 'source_sha256': core.row_sha(source_row), 'status': 'completed', 'label_config': 'nondefault-config', 'topic': 'playback', 'intent': 'complaint', 'sentiment': -1, 'severity': 4, 'entities': [], 'evidence_quote': source_row['review_text'], 'needs_review': False}
            (root / 'records.jsonl').write_text(json.dumps(result)+'\n')
            (root / 'membership.csv').write_text('issue_id,review_id\nissue-playback,r1\n')
            (root / 'calls.jsonl').write_text('')
            db = root / 'restored.sqlite'
            with patch.object(core, 'modelcall', side_effect=AssertionError('Offline only')):
                restore(source, root, db)
            with sqlite3.connect(db) as connection:
                self.assertEqual(connection.execute('SELECT config FROM memberships').fetchone()[0], 'nondefault-config')
            (root / 'records.jsonl').write_text(json.dumps(result)+'\n'+json.dumps(dict(result, review_id='r2', label_config='other'))+'\n')
            with self.assertRaisesRegex(ValueError, 'Mixed'):
                restore(source, root, root / 'rejected.sqlite')
            self.assertFalse((root / 'rejected.sqlite').exists())


if __name__ == '__main__':
    unittest.main()
