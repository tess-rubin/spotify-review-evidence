# Hosted cost calculator

Run `python3 cost/hosted_calculator.py` for offline replay with no key/network. `hosted-measured.json` preserves real pilot usage/timing; `hosted-rates.json` is editable dated USD-per-million-token pricing; `hosted-pilot.json` is the fixed 100,000-review admission projection. Alternate scenarios write `hosted-replay.json` and leave that gate unchanged.

Measured on unchanged cost_100.csv: enrichment input 3,325 tokens and output 2,872 tokens across 100 reviews. Per review: **33.25 input / 28.72 output**. Enrichment $0.001770 after conservative per-call microdollar rounding; pilot including verification and memo $0.002483. Raw provider responses and usage remain in ignored evidence/hosted/attempts, never public credentials.

Published GPT-6 Luna standard rates checked 2026-10-18: $0.10 input, $0.01 cached input and $0.50 output per million tokens. [Official model pricing](https://developers.openai.com/api/docs/models/gpt-6-luna). Reasoning is none; no tools, priority/regional tier or stronger fallback is enabled.

The conservative 100,000-review projection is **$2.04**: no exact-text reuse or cached-input discount assumed, input scaling checks target/pilot text-byte lengths, includes 15% retry allowance, golden evaluation and final verification/memo plus the pilot. Estimated serial API time is 7.3 hours, excluding local full-source scan/export. It is a projection, not a measured completed run. New hosting costs are unavailable; none have been purchased. Existing computer, ordinary electricity and existing subscriptions are excluded from the user's cash cap.

Every hosted request, including retry/evaluation/memo, uses the same persistent ledger and $4.90 ceiling in pipeline/hosted.py. Reservations use a conservative request-byte input-token bound and capped output; unknown charges remain held, not zeroed. Actual usage over a reservation is committed and permanently blocks dispatch pending reconciliation. One interrupted resume-demo request has $0.003025 held with unavailable usage. Check current totals with `python3 pipeline/hosted.py status`.

Synthetic offline tests confirm rate doubling doubles the API subtotal while usage/timing remain unchanged; volume changes do not alter recorded pilot measurements. Tests also cover cumulative reservations, unknown holds, rejection before dispatch, reservation breach accounting/blocking, ID/range checks and the worker lease.

Historical local Gemma/Qwen calculator files remain labeled as historical experiments. Local model tokens are not billed API tokens. Their old measurements are not substituted for the hosted pilot.
