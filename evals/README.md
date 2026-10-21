# Original golden-50 evaluation — public evidence

Published with the owner's explicit authorization. These files are **evaluation outputs only**, never model inputs, few-shot examples, routing data or tuning material. The production classifier and original scores are unchanged.

- `expected.json`: the 50 human answers for topic, intent and severity. Other human fields were not completed and are not invented.
- `predictions.json`: the 50 original frozen hosted-model predictions, with original IDs, source hashes and evidence.
- `comparisons.json`: saved per-review human/model pairs, error fields and severity differences.
- `report.json`: the original aggregate evaluation, including confusions and metric definitions.
- `manifest.json`: source identity and published-file hashes.

Original agreement: 74% topic, 80% intent, 66% severity; severity MAE 0.38; 22/50 exact topic/intent/severity triples. Human annotations can be ambiguous or disagree with contract rules; no post-hoc relabeling was applied. The previously disclosed golden-informed candidate was rejected and never used in the 100,000-review production cohort. Publication does not turn this inspected set into a fresh holdout.

Run `python3 evals/check_saved.py` offline to verify file hashes, all 50 pairs, original scores and comparison consistency. This script has no model client or network calls. The hosted CSV entrypoint rejects files beneath `evals/`. No credentials or working databases are published here.
