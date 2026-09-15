# Completed brightness condition

**9/10 successful**, versus **10/10 clean** on the same fixed states.

A 0.35 brightness multiplier was active at policy steps 30–59; normal input returned at 60. No recovery was enabled.

| State | Clean actions | Brightness outcome / actions | Paired difference |
| --- | ---: | --- | ---: |
| 0 | 76 | Success / 76 | 0 |
| 1 | 78 | Success / 80 | 2 |
| 2 | 85 | Step limit / 220 | censored at 220 |
| 3 | 74 | Success / 83 | 9 |
| 4 | 76 | Success / 74 | -2 |
| 5 | 74 | Success / 72 | -2 |
| 6 | 73 | Success / 75 | 2 |
| 7 | 82 | Success / 81 | -1 |
| 8 | 86 | Success / 81 | -5 |
| 9 | 78 | Success / 82 | 4 |

Median additional actions among the nine pairs that both succeeded: 0.

The single lost success is initial state 2. Its raw video and validated replay show a grasp/transfer failure; the target remained on the table. [Detailed evidence](failure-analysis-brightness-state-02.md).

Artifact checks passed for all ten completed trials: initial RGB images and all first 30 actions matched their clean pairs, perturbation timing was exact, and onset images matched the specified transform.

One interrupted technical attempt was excluded and preserved. This one-task developmental pilot supports an observed counterexample, not a broad or statistically significant robustness claim. The completed occlusion condition succeeded on 0/10 of the same initial states; see report.md for the full paired comparison.
