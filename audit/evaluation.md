# Evaluation audit — 2026-10-18

Scope: read-only review of saved predictions, human-label scoring, isolation controls, and benchmark separation. No inference, classifier changes, prompt changes, label edits, or paid calls. Human answers were used only to recompute scores and inspect evaluation correctness.

## Verified

Independent arithmetic over all 50 completed human rows reproduces the saved results:

| Configuration | Topic accuracy | Intent accuracy | Severity exact | Severity MAE |
|---|---:|---:|---:|---:|
| Gemma baseline | 0.38 | 0.70 | 0.70 | 0.40 |
| Qwen v2 | 0.72 | 0.82 | 0.60 | 0.54 |
| Qwen v3 | 0.72 | 0.82 | 0.66 | 0.46 |
| Paired offline v3 | 0.72 | 0.82 | 0.66 | 0.46 |

All four files have exactly 50 unique expected IDs, with no extra IDs. Current prediction sentiment values and entity list types also satisfy their basic contract ranges/types. The scorer anchors predictions to canonical supplied source hashes and evidence substrings, and keeps invalid/missing predictions in the accuracy denominator. Macro F1 is explicitly reported both across all contract classes and across supported classes. Severity MAE over completed predictions is distinguished from a separately named missing-penalty metric. No numerical scoring error was found in these saved results.

The human file SHA-256 is `45b405ab3890baaeace910e264935dae0e034c5581c9ade8f6d0f826e9382157`. Only topic, intent, and severity have human answers; claims about accuracy of other fields are appropriately withheld. No human examples cover three topic categories, cancellation intent, or severity 5. These are 50 diagnostic examples, not a full-corpus quality estimate.

## Findings

1. **Development text separation needs strengthening.** Direct comparison of canonical source-only CSVs finds zero shared IDs but one exact shared review text between `supplied/cost_100.csv` and `supplied/golden_50_to_label.csv`; `supplied/checkpoint_500.csv` shares three exact texts with the golden file. Existing reports correctly claim ID disjointness, but those inputs are not fully text-disjoint. New development selection should exclude both golden IDs and exact text hashes, using only the source-only golden CSV. Human answers need not be opened for this exclusion. This does not establish answer leakage in prior inference.

2. **The scorer's validity check is narrower than the contract.** `evaluation/evaluate.py:43` validates status, source hash, topic, intent, severity, needs_review, and quote, but does not validate sentiment, entity shape/content, or frozen `label_config` for JSONL input. A future malformed or mislabeled-profile file could still count as a valid prediction for the three primary metrics. The present files pass the omitted basic sentiment/entity checks independently, so current metrics are unaffected. `run_evaluation.py` verifies configuration/code hashes but does not assert each saved record's configuration identity against the frozen configuration.

3. **Isolation evidence is bounded.** `evaluation/audit_isolation.py:16-22` checks the 146 logged new attempts' text-only payloads and frozen prompts/settings. Four Gemma results were reused; this script does not follow their original call payload lineage. The freeze manifest and matching file hashes support unchanged configuration/code, but `configurations_frozen_before_scoring=True` is an assertion based on the recorded workflow, not a timestamp ordering proven by this script. There is no evidence here of label leakage; avoid describing the audit as independently proving historical noninspection or all reused payloads.

4. **The human-answer guard is path-based.** `pipeline/run.py:13` rejects files under `evaluation/human`, while a copied answer-bearing CSV elsewhere would evade that guard. Current prediction workers use canonical source-only input and audited payloads contain review_text only. Maintain that explicit input allowlist and keep human artifacts inaccessible to development benchmark workers; do not rely solely on the path check.

## Decision

Existing human metrics are reproducible and usable as descriptive held-out evaluation of the frozen candidates. They must not select new prompts, rules, routing, or model settings. Benchmark the faster candidate using separately labeled development inputs that exclude golden IDs and exact texts; report whether development targets are synthetic, human, or model-derived. Measure throughput and cash charges separately from correctness. No scaling or new API spending was performed by this audit.

## Remediation completed in this audit turn

- `evaluation/evaluate.py` now validates all classification fields, rejects nonfinite/out-of-range or boolean sentiment, malformed/empty entity strings, and missing schema fields, and enforces frozen configuration identity for known frozen profiles (including the paired policy derivative).
- `evaluation/audit_isolation.py` now follows all four reused Gemma records through the original corpus label, direct cache origin, source text/hash, matching same-configuration result, and matching successful original text-only call. Chained cache origins are rejected. All four pass; 146 new attempts remain audited.
- Isolation verifies `evaluation/frozen/core-at-evaluation.py` against the original frozen core hash when preserved, and separately reports whether current core matches. Historical freeze timing is explicitly self-attested, not independently timestamp-verified. Later infrastructure edits are outside the historical frozen-snapshot claim.
- Five new synthetic tests in `tests/test_evaluation_audit.py` pass. They cover malformed fields, configuration resolution, successful direct lineage, and rejection of a cache chain; no real human answers are test fixtures.
- Offline scoring was rerun for all four prediction files with the hardened evaluator. Accuracy, macro F1, severity MAE, all-three counts, and completion/invalid/missing counts are exactly unchanged. The isolation audit passes with four original reused records traced. No inference or spending occurred.
- The wrapper `evaluation/run_evaluation.py` initially refused current core's later infrastructure changes because it still compared that file to the old hash. The parent was notified to align that wrapper with the preserved snapshot. Direct offline scoring and isolation both completed successfully.

Parent remediation: the evaluation wrapper now verifies the preserved core snapshot against the original manifest while continuing to verify unchanged semantic code and frozen configurations. The complete wrapper and isolation audit both reran successfully offline; no original hash was rewritten.
