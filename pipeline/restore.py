"""Restore saved evidence offline, preserving its classification configuration."""
import argparse
import csv
import gzip
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import core


def records_in(folder):
    path = folder / 'records.jsonl'
    if not path.exists():
        path = folder / 'records.jsonl.gz'
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rt', encoding='utf-8') as handle:
        yield from map(json.loads, handle)


def restore(input_path, grading, db):
    folder = Path(grading)
    configs = {r.get('label_config') for r in records_in(folder) if r['status'] == 'completed'}
    if len(configs) > 1 or any(not isinstance(c, str) or not c.strip() for c in configs):
        raise ValueError('Mixed or missing configurations cannot restore unversioned memberships')
    config = next(iter(configs), None)
    with (folder / 'membership.csv').open(encoding='utf-8') as handle:
        memberships = list(csv.DictReader(handle))
    if memberships and config is None:
        raise ValueError('Memberships require completed records with a configuration')
    core.ingest(input_path, db)
    d = core.dbopen(db)
    try:
        with d:
            completed = set()
            for row in records_in(folder):
                original = d.execute('SELECT row_hash,text_hash,text FROM sources WHERE id=?', (row['review_id'],)).fetchone()
                if original is None or original['row_hash'] != row['source_sha256']:
                    raise ValueError('Source hash mismatch')
                if row['status'] != 'completed':
                    continue
                value = {key: row[key] for key in core.FIELDS}
                core.validate({'results': [dict(value, review_id=row['review_id'])]}, [{'id': row['review_id'], 'text': original['text']}])
                serialized = json.dumps(value, ensure_ascii=False)
                d.execute('INSERT OR REPLACE INTO labels VALUES(?,?,?,?)', (row['review_id'], config, serialized, row.get('cache_source_id')))
                completed.add(row['review_id'])
                if not row.get('cache_source_id'):
                    d.execute('INSERT OR REPLACE INTO cache VALUES(?,?,?,?)', (original['text_hash'], config, row['review_id'], serialized))
            if config is not None:
                d.execute('DELETE FROM memberships WHERE config=?', (config,))
                d.execute('DELETE FROM aggregates WHERE config=?', (config,))
            for member in memberships:
                if member['review_id'] not in completed:
                    raise ValueError('Membership references a missing completed record')
                d.execute('INSERT INTO memberships VALUES(?,?,?)', (member['issue_id'], member['review_id'], config))
            path = folder / 'calls.jsonl'
            if not path.exists():
                path = folder / 'calls.jsonl.gz'
            opener = gzip.open if path.suffix == '.gz' else open
            with opener(path, 'rt', encoding='utf-8') as handle:
                for call in map(json.loads, handle):
                    d.execute('INSERT OR IGNORE INTO calls VALUES(?,?,?,?,?,?)', (call['request_id'], call['run_id'], call['role'], call['phase'], call['outcome'], json.dumps(call)))
    finally:
        d.close()
    return {'label_config': config, 'memberships': len(memberships), 'aggregates': 'invalidated; recompute for restored configuration'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default='supplied/spotify_reviews_18months.csv')
    parser.add_argument('--grading', default='grading')
    parser.add_argument('--db', default='data/full.sqlite')
    args = parser.parse_args()
    print(json.dumps(restore(args.input, args.grading, args.db)))


if __name__ == '__main__':
    main()
