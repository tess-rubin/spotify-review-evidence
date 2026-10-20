# Decision memo — Spotify historical partial cohort

**Recommendation: prioritize playback reliability for the next quarter, with a focused usability workstream and a separate billing-risk triage lane.** This advice uses historical reviews, not evidence of Spotify’s current product state. The cohort contains 100,000 classified reviews out of 660,609 nonempty source reviews; all 660,622 source rows were ingested. It is explicitly partial and source-order selected. Counts below are review records, including separate exact-text duplicate source records; they are not unique customers. Scope: `grading/run.json`.

## Why playback first

Playback leads the required priority ranking: **10,033 complaint/cancellation reviews**, **32,914 severity sum**, and mean severity **3.280574**. Claims: `issue-playback-complaint_count`, `issue-playback-severity_sum`, `issue-playback-mean_severity`. The baseline is a transparent aggregate of ordinal labels, not an estimate of economic harm.

Investigate whether the Samsung update is breaking app startup or playback, and reproduce the failure on the reported device and software version before evaluating compatibility fixes.

> App quite working after last Samsung update on 5-13-22. Not happy had all my music with you and have nothing yet. Before this I have been very happy andno thinking of upgrading. But if I can't depend on you I will have to look elsewhere.

Source: `8311b642-460e-4ef3-b710-bc80010db7d5`; issue: `issue-playback`. Treat this as a concrete regression hypothesis, not proof that the cited update caused all playback complaints.

## Alternatives and trade-offs

**Usability** has more complaint/cancellation records (**12,001**) but a lower severity sum (**31,585**) and mean (**2.631864**). Claims: `issue-usability-complaint_count`, `issue-usability-severity_sum`, `issue-usability-mean_severity`. Prioritize a bounded investigation of song-selection/shuffle predictability alongside reliability; do not interpret this ranking as permission to redesign every control.

Investigate reports of playlists unexpectedly switching to shuffle after updates; verify playback-mode defaults and make the active mode clear and easy to control.

> Bruh hate the update I should be able to lesson to the songs I want not have random ones in my playlist play I want to be able to lesson to them all not Spotify randomly chosing one I hate this update so much pls Spotify get rid of this up date ! It's horrible worst than sound cloud rn

Source: `5359763c-3ecf-45da-a7f1-fb5f23955b30`; issue: `issue-usability`.

**Billing** is a smaller aggregate lane: **2,366 records**, severity sum **6,978**, mean **2.949281**. Claims: `issue-billing-complaint_count`, `issue-billing-severity_sum`, `issue-billing-mean_severity`. Maintain manual triage for serious payment/privacy reports even when their aggregate rank is lower; this corpus contains no validated account-revenue or confirmed-churn data.

Investigate repeated payment failures during debit-card setup, tracing the payment flow and error messaging so users can identify and resolve rejected payments.

> It's annoying I've been trying to add a debit card for the past 4months now, no way I've tried all my cards yet no way it keeps saying payment failed

Source: `72c5cbab-9717-4f45-89ab-85c3eee84c45`; issue: `issue-billing`.

## Reproducible baseline

Complaint/cancellation records only. Priority equals integer severity sum; descending score, then ascending issue ID breaks ties. Means are six-decimal half-up. The complete `membership.csv`, `ranking.csv` and `claims.csv` are in the grading export.

| Rank | Stable issue | Records | Severity sum / priority | Mean severity |
|---:|---|---:|---:|---:|
| 1 | issue-playback | 10033 | 32914 | 3.280574 |
| 2 | issue-usability | 12001 | 31585 | 2.631864 |
| 3 | issue-billing | 2366 | 6978 | 2.949281 |
| 4 | issue-catalog | 2518 | 6914 | 2.745830 |
| 5 | issue-other | 2994 | 6215 | 2.075818 |
| 6 | issue-downloads | 1335 | 4298 | 3.219476 |
| 7 | issue-access | 1072 | 3972 | 3.705224 |
| 8 | issue-support | 102 | 289 | 2.833333 |

Exact table claims by issue:
- issue-playback: `issue-playback-complaint_count`, `issue-playback-severity_sum`, `issue-playback-priority_score`, `issue-playback-mean_severity`.
- issue-usability: `issue-usability-complaint_count`, `issue-usability-severity_sum`, `issue-usability-priority_score`, `issue-usability-mean_severity`.
- issue-billing: `issue-billing-complaint_count`, `issue-billing-severity_sum`, `issue-billing-priority_score`, `issue-billing-mean_severity`.
- issue-catalog: `issue-catalog-complaint_count`, `issue-catalog-severity_sum`, `issue-catalog-priority_score`, `issue-catalog-mean_severity`.
- issue-other: `issue-other-complaint_count`, `issue-other-severity_sum`, `issue-other-priority_score`, `issue-other-mean_severity`.
- issue-downloads: `issue-downloads-complaint_count`, `issue-downloads-severity_sum`, `issue-downloads-priority_score`, `issue-downloads-mean_severity`.
- issue-access: `issue-access-complaint_count`, `issue-access-severity_sum`, `issue-access-priority_score`, `issue-access-mean_severity`.
- issue-support: `issue-support-complaint_count`, `issue-support-severity_sum`, `issue-support-priority_score`, `issue-support-mean_severity`.

## Limits and next decision

The cohort is self-selected, historical, partial and not population-representative. Primary topics are coarse and do not establish root causes. Exact duplicates contribute separate records to business counts, so repeated language can concentrate scores. Golden-50 disagreement is substantial; provenance and schema checks do not prove label correctness. Sentiment and review flags lack completed human gold labels, and entities were not extracted. A golden-informed experimental prompt was rejected; the original frozen classifier produced this ranking.

Start with reproducible failure investigations and inspect source evidence before committing a large roadmap. Compare representative device/update paths and control states, and define prospective product measurements before claiming improvement. The reviews alone cannot establish causal retention gains, revenue impact or actual cancellation outcomes.
