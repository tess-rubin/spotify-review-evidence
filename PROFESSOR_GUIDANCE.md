# Class 7 alignment

Source: [professor’s presentation](https://haas-ai-classes-fall-26.vercel.app/class7.html#/checkpoint-invalidation), reviewed October 18, 2026.

| Guidance applied | Implementation evidence |
|---|---|
| Separate building from running; choose a fixed workflow when suitable. | `pipeline/run.py`; four bounded model roles, no autonomous swarm. |
| Reuse compatible results and preserve source IDs. | Versioned SQLite cache; direct originals; `self-check.json`. |
| Invalidate changed stages and their dependents. | `pipeline/checkpoints.py`; memo changes preserve labels; regression tests. |
| Persist valid outputs before acknowledging progress. | Transactional writes; real SIGINT recording and snapshots. |
| Share limits, bound retries, measure before scaling. | One worker, spend reservations, retry tests, cold/warm pilot and 500 checkpoint. |
| Verify blindly and ground writing in saved aggregates. | Separate verifier prompt, disagreement report, integer ranking, citation validation. |

Human evaluation is complete, with frozen configurations and a before-error-inspection fix. Remaining gaps: historical Gemma injection failure, remaining classifier disagreements and annotation ambiguities, 10,000/full execution incomplete, and grader access pending.
