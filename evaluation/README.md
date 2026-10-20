# Human evaluation: completed, isolated from inference and tuning

All 50 topic/intent/severity answers in `human/labels.csv` validate. The file is unchanged. Its spreadsheet-formatted timestamps differ from the original seconds-resolution timestamps; only original supplied source values are used for inference and hashes. IDs and review texts match exactly. Timestamp presentation differences are retained as warnings in `human-validation.json`, not treated as changed labels or classification inputs.

`frozen/improvement-plan.json` records classifier configurations and the rubric-only severity policy frozen **before reading evaluation errors**. The change was motivated by three pre-existing development-pilot violations and a synthetic test, not by the 50 human answers. Configuration and implementation hashes are retained. The synthetic test improves from 10/12 to 11/12 exact triples; three development inconsistencies are corrected with the other 97 pilot results unchanged.

The local prediction worker reads only `prediction-input.csv` with the six original source columns. It sends only `review_text` to the model. It never opens the human answer file or score reports. The evaluator can read human answers for scoring and descriptive error inspection, and has no model access. Golden comparisons are not training examples, routing rules, normalization rules or prompt examples.

Reproduce saved scoring offline:

```sh
python3 evaluation/run_evaluation.py
python3 evaluation/audit_isolation.py
```

`summary.json` contains all configurations. Each `results/<name>/` folder contains a report, topic/intent confusion matrices, and every source-linked comparison. `report.json` identifies the frozen Qwen v3 candidate. `REPORT.md` and `ERROR_ANALYSIS.md` explain the results and limitations. Human answers and row-level comparisons remain outside the website.

The all-label macro F1 uses all eight contract topics and all five intents, assigning zero F1 to absent undefined classes. Supported-class macro F1 and class counts are also shown. Missing/invalid predictions stay in the denominator; none are missing in this evaluation. Severity MAE is calculated over completed predictions, with a separately named missing-penalty metric for incomplete evaluations. Topic/intent/severity are the completed human fields. Other label fields are blank and are not scored as though human answers existed.

The paired-policy result transforms the same frozen Qwen v2 outputs offline to measure the policy's effect without inference variation. It is clearly marked an evaluation-only derivative, with **zero new model calls**, and is not offered as provider-call evidence. Independently executed v3 inference produced the same paired metrics.

The 50 reviewed answers are now diagnostic evidence. Do not iterate prompts, rules or model settings to raise these scores. Any subsequent improvement needs separate rubric-derived development data and an independently maintained future holdout. No human answer was edited to improve agreement.

## Hosted experiment disclosure

The original hosted production profile was frozen before its golden-50 score (74% topic, 80% intent, 66% severity; 22/50 all-three). A subsequent one-off golden-error-informed trial ran under a temporary user instruction; its improved scores are development results and are not independent accuracy. The user withdrew that instruction, so the candidate was rejected for production and its command retired. Human answers never appeared in model prompts. Future revisions must use the independent development checkpoints and contract tie rules. The fresh-holdout directory reserves new synthetic functional cases and 50 blind real cases; real held-out accuracy remains pending human labels.
