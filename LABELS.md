# Labels and role boundaries

The exact eight topic labels and five intent labels follow `supplied/GRADING_CONTRACT.md`. Classify only review text; stars, dates, likes and app version stay outside model inputs. Topic ties use the highest supported severity, then the first specific problem. For positive reviews, use the first specific praised feature; generic praise/criticism is `other`.

Synthetic rubric illustrations, not golden answers:

| Text | Topic | Intent | Severity |
|---|---|---|---|
| I pay for Premium but music crashes every time I press play. | playback | complaint | 4 |
| The price is too high, so I am cancelling. | billing | cancellation | 2 |
| Please add a sleep timer. | usability | request | 1 |
| Bad app. | other | complaint | 2 |
| Great app. | other | praise | 1 |
| Offline downloads vanished and I cannot play saved music offline. | downloads | complaint | 4 |

These describe intended interpretation, not a claim that every model output matches. Severity 5 requires explicit serious financial, privacy or data harm; anger, price, crash or cancellation alone is insufficient. Missing context should trigger `needs_review`. Sentiment must be finite and between -1 and 1.

The hosted classifier uses GPT-6 Luna with reasoning `none`, at most 50 reviews per request, compact schema keys and a capped output. Each opaque request ID must appear exactly once and maps back to one original ID in code. The model supplies topic, intent, severity, sentiment and needs_review. Code supplies the full unchanged text as an exact evidence quote and an empty entity array. **Entities are not extracted.** Full-text evidence establishes source provenance, not interpretive correctness.

Blind verification receives deterministic sample texts with no original predictions or human answers. It uses the same model; its disagreement rate is a consistency check, not independent ground-truth accuracy. Verification never overwrites originals. Golden answers are confined to offline evaluation, never prompts, tuning or routing.

Grouping is entirely code: one stable `issue-<topic>` membership for every complaint/cancellation record, including separate exact-text duplicate source records. Integer severity sums determine ranking, then ascending issue ID breaks ties. Means use six-decimal half-up rounding. No grouping API call occurs.

Memo generation receives saved aggregates and at most two exact source examples per issue. It must cite known issue IDs, review IDs and exact quotes. Code rejects digit-containing action claims, but substantive prose grounding and non-digit numerical claims still require human review. The memo and `claims.csv` expose the aggregate metrics used. Historical local Gemma/Qwen experiments remain separate and do not count as hosted classifications.
