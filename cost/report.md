# Cost and runtime: measured, projected, unavailable

Measured on the unchanged `cost_100.csv`: 100 completed, 0 remaining; 100 unique texts. Cold result cache was empty. Input SHA256: `c884ac3b9be5066995d5063f96ad9af6e5e082975788c1684c4f6b6ea661dd0e`.

| Measurement | Cold | Warm |
|---|---:|---:|
| Wall-clock seconds | 70.898992 | 0.011824 |
| Enrichment attempts | 100 | 0 |
| Verification attempts | 10 | 0 |
| Group attempts | 4 | 0 |
| Memo attempts | 4 | 0 |
| API charge USD | 0 | 0 |
| Local compute USD | unknown | unknown |

Cold throughput: 1.410457 input reviews/second. API charge per thousand inputs and per completed record is $0. API charge excludes local hardware/electricity. Under the clarified user budget, existing hardware, ordinary electricity and existing subscriptions do not count toward the cash cap; any new paid charge still counts. Independent verification disagreed on 3/10 reviews. Subsequent 50-label human agreement is recorded separately in evaluation/REPORT.md; these pilot timings and outputs remain unchanged.

Settings: Ollama gemma3:1b, Q4_K_M; digest in call logs; temperature 0, seed 42, context cap 16,384, output cap 1,024, unsupported effort parameter omitted, batch size 1, concurrency 1, fallback quota 0. Began with batches of 10; failed diagnostic formats were retained and excluded from the clean pilot. No provider prompt-cache discount is claimed.

The 500-review checkpoint is complete and refreshes the forecasts below. Its final resume segment timing excludes the earlier pilot and interrupted/resumed segments, which have their own logs and measurements; it is not a cold 500-review timing.

| Scenario | Exact reuse | Distinct classifications | Estimated hours | API USD | Additional local cash USD | Economic total USD |
|---|---|---:|---:|---:|---:|---|
| base | False | 660609 | 159.557 | 0 | 0 | unknown |
| conservative | False | 660609 | 179.893 | 0 | 0 | unknown |
| base | True | 484189 | 116.950 | 0 | 0 | unknown |
| conservative | True | 484189 | 131.854 | 0 | 0 | unknown |

These are stage-specific estimates, not full-run measurements. The eight-topic taxonomy bounds group and memo calls; verification is 10% capped at 10, fixed overhead is added once, retry assumptions are 2%/15%, fallback is zero. An unchanged warm run reuses downstream artifacts too. $4.90 caps model-call admission; no paid route exists. The user excludes existing hardware, ordinary electricity and existing subscriptions; the cash cap covers new charges, and no new paid service is enabled.

Scaling decision: hold 10,000/full gates. The actual injection test failed, classifier quality still requires repair and full-run quality is not established. Jev/cloud comparison is unavailable without keys; no imaginary quality, prices or usage are substituted.

Replay: `python3 cost/calculator.py`. Tests demonstrate unchanged recorded pilot observations when projected volume changes, actual zero-API arithmetic under doubled rates, and nonzero rate scaling using a clearly synthetic billing fixture.

2026-10-18 follow-up: the real-money cap excludes existing hardware, ordinary electricity and existing subscriptions. No paid provider is enabled; new API charges remain $0. The three-agent audit corrected portable checkpoint replay and per-record enrichment overhead. The newer separate-development model comparison and stage-specific projections are in `../experiments/faster-classifier/REPORT.md` and `faster_benchmark.json`; this report's recorded Gemma pilot remains historical evidence.
