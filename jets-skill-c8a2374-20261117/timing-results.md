## Final PHYSLITE-to-histogram timing

Each job processed 20,000 events with one worker on CPU 3. The controller interleaved fresh processes and excluded the first round. The three retained rounds give the arithmetic mean and sample standard deviation (SD). The monotonic wall clock includes process startup and output serialization. Filesystem and CVMFS caches could be warm. The production journal records 265 exact histogram checks. [Production timing receipts](evidence/timing/production/compact.json)

A used stock AnalysisBase. B used the framework with CorrectionLib. Each ran a framework job that wrote an ntuple and a separate process that read it, filled the histogram, and saved it. C read the original PHYSLITE and saved the histogram in one direct Python job. The read-without-corrections control includes startup, reading and output work. In that control B also uses the stock workflow.

### Wall times

All values are in seconds. Total SD uses the summed framework and histogram times for each retained job.

| Scope | Workload | A framework | A ntuple read + hist | A total | B framework | B ntuple read + hist | B total | C direct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Small-R | Read without corrections | 4.43 ± 0.05 | 0.25 ± 0.00 | 4.67 ± 0.05 | 5.47 ± 1.09 | 0.25 ± 0.00 | 5.71 ± 1.09 | 0.49 ± 0.00 |
| Small-R | Nominal calibration | 10.56 ± 0.09 | 0.27 ± 0.00 | 10.84 ± 0.09 | 10.66 ± 0.64 | 0.29 ± 0.03 | 10.95 ± 0.62 | 2.52 ± 0.01 |
| Small-R | Full systematics | 128.72 ± 2.02 | 3.47 ± 0.06 | 132.19 ± 2.00 | 137.91 ± 2.94 | 3.52 ± 0.07 | 141.42 ± 2.98 | 11.30 ± 0.42 |
| Large-R | Read without corrections | 4.48 ± 0.15 | 0.25 ± 0.00 | 4.74 ± 0.15 | 5.01 ± 0.27 | 0.25 ± 0.01 | 5.26 ± 0.28 | 0.44 ± 0.02 |
| Large-R | Nominal calibration | 8.56 ± 0.30 | 0.30 ± 0.04 | 8.86 ± 0.34 | 8.74 ± 0.22 | 0.28 ± 0.01 | 9.02 ± 0.22 | 1.80 ± 0.08 |
| Large-R | Full systematics | 99.94 ± 4.19 | 6.35 ± 0.53 | 106.29 ± 4.00 | 101.82 ± 2.90 | 6.09 ± 0.09 | 107.91 ± 2.95 | 2.88 ± 0.09 |
| Combined | Read without corrections | 5.19 ± 0.48 | 0.27 ± 0.02 | 5.46 ± 0.49 | 4.57 ± 0.14 | 0.26 ± 0.01 | 4.84 ± 0.15 | 0.52 ± 0.02 |
| Combined | Nominal calibration | 11.78 ± 0.27 | 0.31 ± 0.01 | 12.09 ± 0.28 | 12.42 ± 0.34 | 0.32 ± 0.03 | 12.74 ± 0.35 | 3.23 ± 0.07 |
| Combined | Full systematics | 259.54 ± 15.17 | 9.37 ± 0.21 | 268.91 ± 15.38 | 268.03 ± 8.48 | 9.29 ± 0.03 | 277.32 ± 8.48 | 12.83 ± 0.00 |

### Matched comparisons

Each ratio divides retained means. The gate allows sample SD / mean up to 5% and an individual deviation from its cohort median up to 10%. Stock anchor deviations may be up to 10%. The B framework budget allows B/A up to 1.20× for nominal and full calibration. The full-systematics goal is A/C at least 10×. Same-round ratios on both sides of a threshold leave that decision unresolved. Flagged values describe the observed runs. A B/A decision uses both framework legs and the stock framework anchors. An end-to-end comparison uses all measured legs of its two paths and the stock anchors.

| Scope | Workload | B/A framework | A/C workflow | B/C workflow |
| --- | --- | --- | --- | --- |
| Small-R | Read without corrections | 1.24× · stock control · quality flagged (B framework) | 9.63× · quality passed | 11.77× · quality flagged (B framework, B total) |
| Small-R | Nominal calibration | 1.01× · quality flagged (B framework) | 4.31× · quality passed | 4.35× · quality flagged (B framework, B ntuple read + histogram, B total) |
| Small-R | Full systematics | 1.07× · within budget (1.20×) | 11.70× · goal met (10.00×) | 12.51× · quality passed |
| Large-R | Read without corrections | 1.12× · stock control · quality flagged (B framework) | 10.69× · quality passed | 11.88× · quality flagged (B framework, B total) |
| Large-R | Nominal calibration | 1.02× · within budget (1.20×) | 4.93× · quality flagged (A ntuple read + histogram) | 5.02× · quality passed |
| Large-R | Full systematics | 1.02× · within budget (1.20×) | 36.96× · quality flagged (A ntuple read + histogram) | 37.52× · quality passed |
| Combined | Read without corrections | 0.88× · stock control · quality flagged (A framework) | 10.49× · quality flagged (A framework, A ntuple read + histogram, A total) | 9.30× · quality passed |
| Combined | Nominal calibration | 1.05× · within budget (1.20×) | 3.74× · quality passed | 3.94× · quality flagged (B ntuple read + histogram) |
| Combined | Full systematics | 1.03× · quality flagged (A framework) | 20.96× · quality flagged (A framework, A total) | 21.61× · quality passed |

### Stock anchors

The production controller repeated the combined stock full-systematics job between rounds and after the last round. The drift check compares each anchor with the median of the anchors for the same leg.

| Leg | Anchor seconds | Anchor median (s) | Maximum deviation | Drift check |
| --- | --- | --- | --- | --- |
| Framework | 250.77, 252.55, 250.92, 259.49 | 251.73 | 3.1% | Pass |
| Ntuple read + histogram | 9.24, 9.27, 9.19, 9.28 | 9.26 | 0.7% | Pass |
| Total | 260.01, 261.82, 260.11, 268.77 | 260.96 | 3.0% | Pass |

### Bounded paired rechecks

Each recheck uses its own retained runs and its own stock brackets. The brackets are compared with the median of retained stock runs in that recheck. A qualified recheck supplies the decision for its pair. Original cohort values remain in the tables above.

#### Small-R · Nominal calibration · A/B

1.04× · quality flagged (A framework). Same-round ratios were 1.05×, 1.09×, 0.99×. [Paired recheck receipt](evidence/timing/recheck-AB-small-nominal-001/summary.json)

| Path | Leg | Mean ± SD (s) |
| --- | --- | --- |
| A | framework | 11.23 ± 0.61 |
| B | framework | 11.69 ± 0.37 |

| Leg | Bracket seconds | Retained stock median (s) | Maximum deviation | Drift check |
| --- | --- | --- | --- | --- |
| Framework | 11.27, 11.25 | 11.03 | 2.2% | Pass |
| Ntuple read + histogram | 0.29, 0.28 | 0.29 | 2.4% | Pass |
| Total | 11.56, 11.53 | 11.32 | 2.1% | Pass |

#### Large-R · Full systematics · A/C

33.85× · goal met (10.00×). Same-round ratios were 32.25×, 34.52×, 34.89×. [Paired recheck receipt](evidence/timing/recheck-AC-large-full-001/summary.json)

| Path | Leg | Mean ± SD (s) |
| --- | --- | --- |
| A | framework | 97.69 ± 0.66 |
| A | ntuple read + histogram | 6.05 ± 0.15 |
| A | total | 103.74 ± 0.78 |
| C | total | 3.06 ± 0.11 |

| Leg | Bracket seconds | Retained stock median (s) | Maximum deviation | Drift check |
| --- | --- | --- | --- | --- |
| Framework | 97.86, 97.35 | 97.77 | 0.4% | Pass |
| Ntuple read + histogram | 5.99, 6.18 | 5.98 | 3.4% | Pass |
| Total | 103.86, 103.53 | 103.72 | 0.2% | Pass |

#### Combined · Full systematics · A/C

20.09× · goal met (10.00×). Same-round ratios were 20.08×, 20.23×, 19.96×. [Paired recheck receipt](evidence/timing/recheck-AC-combined-full-001/summary.json)

| Path | Leg | Mean ± SD (s) |
| --- | --- | --- |
| A | framework | 250.24 ± 0.77 |
| A | ntuple read + histogram | 9.39 ± 0.15 |
| A | total | 259.64 ± 0.89 |
| C | total | 12.92 ± 0.10 |

| Leg | Bracket seconds | Retained stock median (s) | Maximum deviation | Drift check |
| --- | --- | --- | --- | --- |
| Framework | 248.52, 273.58 | 250.65 | 9.1% | Pass |
| Ntuple read + histogram | 9.29, 9.65 | 9.38 | 2.8% | Pass |
| Total | 257.81, 283.23 | 260.11 | 8.9% | Pass |

#### Combined · Full systematics · A/B

1.04× · quality flagged (stock framework anchors). Same-round ratios were 1.04×, 1.04×, 1.04×. [Paired recheck receipt](evidence/timing/recheck-AB-combined-full-001/summary.json)

| Path | Leg | Mean ± SD (s) |
| --- | --- | --- |
| A | framework | 250.60 ± 2.80 |
| B | framework | 260.48 ± 3.37 |

| Leg | Bracket seconds | Retained stock median (s) | Maximum deviation | Drift check |
| --- | --- | --- | --- | --- |
| Framework | 278.78, 250.91 | 249.61 | 11.7% | Flagged |
| Ntuple read + histogram | 9.87, 9.24 | 9.23 | 7.0% | Pass |
| Total | 288.65, 260.14 | 258.94 | 11.5% | Flagged |

### Combined job compared with two standalone jobs

For each path and workload, the standalone sum adds the small-R and large-R totals from the same round. Its SD describes those three sums. The ratio divides the measured combined mean by the standalone-sum mean.

| Workload | Path | Combined (s) | Small-R + Large-R (s) | Combined / sum | Quality flags |
| --- | --- | --- | --- | --- | --- |
| Read without corrections | A | 5.46 ± 0.49 | 9.41 ± 0.17 | 0.58× | Combined |
| Read without corrections | B | 4.84 ± 0.15 | 10.98 ± 1.30 | 0.44× | Small-R, Large-R, standalone sums |
| Read without corrections | C | 0.52 ± 0.02 | 0.93 ± 0.01 | 0.56× | Pass |
| Nominal calibration | A | 12.09 ± 0.28 | 19.69 ± 0.26 | 0.61× | Pass |
| Nominal calibration | B | 12.74 ± 0.35 | 19.97 ± 0.78 | 0.64× | Small-R |
| Nominal calibration | C | 3.23 ± 0.07 | 4.31 ± 0.07 | 0.75× | Pass |
| Full systematics | A | 268.91 ± 15.38 | 238.49 ± 5.01 | 1.13× | Combined |
| Full systematics | B | 277.32 ± 8.48 | 249.34 ± 4.85 | 1.11× | Pass |
| Full systematics | C | 12.83 ± 0.00 | 14.18 ± 0.47 | 0.91× | Pass |

### Full-systematics process resources

CPU time sums user and system time across each job's legs and averages the retained jobs. Peak RSS is the largest process peak across legs and rounds. CPU-slot I/O wait is a guest counter observed during the legs.

| Scope | Path | Mean process CPU (s) | Maximum peak RSS (MiB) | Mean guest CPU-slot I/O wait (s) |
| --- | --- | --- | --- | --- |
| Small-R | A | 129.40 | 1,255 | 0.68 |
| Small-R | B | 137.67 | 1,318 | 1.63 |
| Small-R | C | 11.22 | 438 | 0.00 |
| Large-R | A | 104.06 | 1,235 | 0.29 |
| Large-R | B | 106.16 | 1,282 | 0.20 |
| Large-R | C | 2.85 | 435 | 0.00 |
| Combined | A | 265.59 | 1,305 | 0.56 |
| Combined | B | 271.14 | 1,397 | 2.88 |
| Combined | C | 12.76 | 520 | 0.00 |
