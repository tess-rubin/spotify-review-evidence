# Pipeline audit — 2026-10-18

Scope: read-only code/contract review and read-only SQLite queries. No inference, scaling, human-answer files, human comparisons, or evaluation reports were opened. No API charges incurred. Findings below are independent of human evaluation outcomes.

## Findings

1. **High — scale gate silently selects the old Gemma classifier.** `pipeline/run.py` defaults to `qwen-v3` and calls `load_profile`, while `pipeline/gate.py:4-16` imports the default `core` configuration and never loads a profile. `core.py:13` defaults to Gemma. Gate prerequisite checks only an unscoped file's `status=complete`, not its label configuration, input hash, or benchmark acceptance. Consequently a Qwen pilot does not control the configuration used at 10,000/full scale. Fix: explicit profile argument shared by every CLI; resolve configuration once; require predecessor measurements and quality evidence with matching profile/configuration and source hash before admission.

2. **High — ingestion silently drops new IDs with colliding ordinals when a DB is reused.** `pipeline/core.py:25,39-47` assigns ordinal from each input and uses `INSERT OR IGNORE` against both ID and UNIQUE ordinal. Ingesting a different CSV into an existing database can ignore unseen IDs without error. `execute` then processes all DB rows, while its report attaches the newly supplied input file's hash. Fix: bind a DB to a source identity, reject mismatched input scope, or allocate ordinal explicitly; reconcile exact ID/count/hash identity before inference and exports. This is a code-path finding, not a claim that the saved full database is corrupt.

3. **Medium — cache identity does not include the effective output schema or preprocessing implementation.** `core.py:16` hashes CONFIG, whose schema field is a name. Actual schema construction, prompt rewriting, automatic full-text evidence extraction, and response transformation occur in `modelcall` outside that object. A code/schema change without a manual version bump can reuse incompatible completed labels (`core.py:179-184`). `checkpoints.py` compares versions but execution does not enforce snapshot compatibility. Fix: fingerprint the effective request contract and postprocessing version; enforce manifest comparison in resume. Existing explicit configuration changes do correctly produce separate label keys.

4. **Medium — recommendation validation does not establish the promised absence of numerical claims.** `core.py:validate_downstream` rejects digit characters only. Claims such as “all users,” “half the reviewers,” or “twice as many complaints” pass without checking saved aggregates. Evidence quotes and review IDs are checked, which is good, but this does not validate prose semantics. Fix: use bounded recommendation templates with verified claim references or a separate semantic claim validator and human release review. Do not describe current validation as proving all numerical claims.

5. **Medium — exported scope/completion metadata lacks a structured release status.** `core.py:export` writes every unresolved nonempty record as quarantined with `not_classified_model_execution_pending`, permitted by the contract for accounted failures, but `run.json` only says “see records.” Downstream consumers can mistake accounted rows for completed classifications unless they recalculate status. Fix: publish completed/nonempty/unresolved/empty counts, active config, quality state, and `completion_status=incomplete`; keep failure accounting separate from successful coverage in dashboard and package gates.

6. **Medium — restore can attach memberships to the wrong classifier.** `pipeline/restore.py` restores labels using each record's actual `label_config`, but restores memberships with imported default `LABEL_CONFIG`. This works for the current Gemma full export and fails as a general Qwen/custom-profile restore. It also does not restore aggregates. Fix: read declared export config, reject mixed ambiguity, preserve membership config explicitly, and recompute aggregates offline for that same config.

## Verified strengths and saved-state checks

- The source table in `data/full.sqlite` contains **660,622** rows and **13** quarantined empty texts.
- That DB has **66,577** classified rows for its saved Gemma configuration, comprising **479** direct originals and **66,098** aliases. A read-only query found **zero** aliases with a missing original, alias chain, changed result, or differing source text.
- `data/qwen-v3-pilot.sqlite` contains **100** source rows and **100** direct classifications under a distinct config; zero invalid aliases. This is evidence of existing state, not a newly run benchmark.
- Normal enrichment model inputs are text-only. IDs are reattached by code for single-review classification. The validator checks enum/range/type constraints and exact nonempty source substrings before label writes.
- Membership includes only complaint/cancellation records; stable issue IDs are `issue-<topic>`. Aggregation uses integer severity sums, descending sum then ascending ID sorting, and Decimal half-up six-decimal means. Exact-text aliases remain separate records and count separately.
- Current adapter is local Ollama only, has no paid route, and records API cost zero. A paid provider integration would need a real cash reservation amount and reconciliation rather than the current zero reservations.

## Limitations / release recommendation

This audit did not rerun inference, the supplied checker, deployment, or benchmark, and did not assess human agreement. Keep scale paused until the active classifier is explicit, its development benchmark and quality evidence are matched to its config, and source identity is enforced. The coarse topic-level issue taxonomy is deterministic and contract-compatible but provides limited root-cause detail; generated group titles are cached without affecting membership.

## Remediation completed during this audit

- `pipeline/gate.py` now requires an explicit static profile, predecessor measurement/database, and config-bound synthetic quality evidence. It requires complete predecessor scope (500 before 10,000; 10,000 before full), matching label_config, the canonical source checksum, and an identical saved run in the predecessor DB. Missing/failed injection evidence is rejected. The old bypass flag was removed. Target databases are isolated under `data/gates/<label_config>/`; saved direct originals are seeded only under that config and normal execution resolves duplicate aliases.
- Quality evidence is deliberately explicit JSON: `{"label_config":"...","cases":[{"injection_resisted":true},...]}`. Old unversioned lists cannot authorize a new classifier.
- `pipeline/restore.py` now derives the membership config from completed export records, rejects mixed or missing config before importing records, validates restored label schema/evidence, rejects unknown membership review IDs, and invalidates old aggregates for the restored config. It remains entirely offline.
- `python3 -m unittest tests.test_pipeline_audit -v`: **3 tests passed**. Tests cover same-config/scope/quality gating, mandatory explicit scale controls, nondefault-config membership restore, and pre-mutation rejection of mixed configs. Model-call functions are patched to fail if invoked. No model inference or scaling was run.

The other findings remain open or assigned to another auditor; this remediation does not claim a complete classifier-quality or release approval.
