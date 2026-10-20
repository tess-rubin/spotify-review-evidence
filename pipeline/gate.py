"""Explicit, profile-isolated scale gates. Importing this module never runs inference."""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import core
from pipeline.classifier_profile import load_profile


def validate_evidence(previous, quality, config, expected_count):
    if previous.get('label_config') != config or previous.get('status') != 'complete':
        raise ValueError('Previous gate must be complete under the selected label_config')
    if previous.get('input_count') != expected_count or previous.get('remaining') != 0:
        raise ValueError('Previous gate has the wrong scope or unfinished rows')
    if not isinstance(quality, dict) or quality.get('label_config') != config:
        raise ValueError('Quality evidence must identify the selected label_config')
    cases = quality.get('cases')
    if not isinstance(cases, list) or not cases:
        raise ValueError('Quality evidence needs nonempty synthetic cases')
    if any(case.get('injection_resisted') is not True for case in cases):
        raise ValueError('Known prompt-injection failure; repair and retest before scaling')


def seed_previous(source, target, config):
    """Copy matching originals/calls only; normal execution resolves exact duplicates."""
    src = sqlite3.connect(f'file:{Path(source).resolve()}?mode=ro', uri=True)
    src.row_factory = sqlite3.Row
    dst = core.dbopen(target)
    try:
        with dst:
            for row in src.execute('SELECT l.*,s.row_hash,s.text_hash FROM labels l JOIN sources s ON s.id=l.id WHERE l.config=? AND l.cache_source_id IS NULL', (config,)):
                original = dst.execute('SELECT row_hash FROM sources WHERE id=?', (row['id'],)).fetchone()
                if original is None or original[0] != row['row_hash']:
                    raise ValueError('Predecessor source identity differs')
                dst.execute('INSERT OR IGNORE INTO labels VALUES(?,?,?,NULL)', (row['id'], config, row['result']))
                dst.execute('INSERT OR IGNORE INTO cache VALUES(?,?,?,?)', (row['text_hash'], config, row['id'], row['result']))
            for row in src.execute('SELECT * FROM calls'):
                dst.execute('INSERT OR IGNORE INTO calls VALUES(?,?,?,?,?,?)', tuple(row))
            for row in src.execute('SELECT * FROM artifacts'):
                dst.execute('INSERT OR IGNORE INTO artifacts VALUES(?,?)', tuple(row))
    finally:
        dst.close()
        src.close()


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('gate', choices=['10000', 'full'])
    parser.add_argument('--profile', required=True, help='Static pipeline/configs profile name')
    parser.add_argument('--spend-cap', required=True, type=float)
    parser.add_argument('--previous-measurement', required=True, type=Path)
    parser.add_argument('--previous-db', required=True, type=Path)
    parser.add_argument('--quality-evidence', required=True, type=Path)
    args = parser.parse_args(argv)
    if not 0 < args.spend_cap < 5:
        parser.error('Cap must be positive and below $5')
    if Path(args.profile).name != args.profile:
        parser.error('Profile must be a static profile name')
    load_profile(args.profile)
    previous = json.loads(args.previous_measurement.read_text())
    quality = json.loads(args.quality_evidence.read_text())
    try:
        validate_evidence(previous, quality, core.LABEL_CONFIG, 500 if args.gate == '10000' else 10000)
        filename = 'checkpoint_500.csv' if args.gate == '10000' else 'analysis_10000.csv'
        if previous.get('input_sha256') != core.sha(core.ROOT / 'supplied' / filename):
            raise ValueError('Previous measurement input checksum does not match canonical gate input')
        src = sqlite3.connect(f'file:{args.previous_db.resolve()}?mode=ro', uri=True)
        try:
            stored = src.execute('SELECT payload FROM runs WHERE id=?', (previous.get('run_id'),)).fetchone()
            if stored is None or json.loads(stored[0]) != previous:
                raise ValueError('Previous measurement does not match its database run')
        finally:
            src.close()
    except (ValueError, sqlite3.Error) as exc:
        parser.error(str(exc))
    name = 'analysis10000' if args.gate == '10000' else 'full'
    # Config digest isolates even two revisions sharing the same profile filename.
    db = core.ROOT / 'data' / 'gates' / core.LABEL_CONFIG / (name + '.sqlite')
    input_path = core.ROOT / 'supplied' / ('analysis_10000.csv' if args.gate == '10000' else 'spotify_reviews_18months.csv')
    core.ingest(input_path, db)
    seed_previous(args.previous_db, db, core.LABEL_CONFIG)
    core.execute(db, input_path, args.spend_cap, phase='resume', name=args.profile + '-' + name)


if __name__ == '__main__':
    main()
