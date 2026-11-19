# Chapter outline

| Chapter | Speaking time | Audience question | Evidence on screen |
| --- | ---: | --- | --- |
| C1 · What do we need to reproduce? | 2 min | Where do the small- and large-radius prescriptions enter the same analysis? | The original PHYSLITE event, two collections, 119 and 219 configured states, and the two histogram definitions. Show the shared names and distinct small-radius weights and large-radius mass-resolution variations. |
| C2 · Where can the calculations be shared? | 3 min | Which inputs and numerical operations really are common? | Editable diagram from constituent inputs to shared EtaJES and ordinary jet-uncertainty code. Trace the small-radius pile-up, GSC and NNJVT path and the large-radius JMS and forward-folded JMR path. Explain the difference between the original framework, the replacement framework and direct Python. |
| C3 · Does the same jet get the same result? | 3 min | Can we follow an original jet through its variations without a selection hiding a discrepancy? | Small- and large-radius original-versus-converted spectra with residuals, then a compact all-state summary. Use the 604 MeV first-jet discrepancy to explain why neutral event density matters. Put remaining variables and exact input/stream details in backup. |
| C4 · When does combining the work pay? | 4 min | How much do we save by reading and evaluating the collections together? | Measured 40-leaf combined read, 12.83 s together versus 14.18 s separately for C, framework budget and the most consequential tested optimization. Show the published measurement boundary on the visual. Explain the high I/O wait observed in the stock pilot before interpreting combined timing. |

The first three chapters establish the event sample and the physics agreement needed to interpret the last one. The numerical and timing evidence comes from the same original PHYSLITE file, and each production endpoint writes its requested histogram. The input-binding example, early phase diagnostic and detailed collection-specific optimization tables are available in backup.

| Slide | Subject and evidence |
| --- | --- |
| S001 | Why an analysis using two jet sizes needs to know which numerical routines and processing costs it can share. |
| S002 | Particle-flow and groomed UFO jets in the same 20,000 events. The initialized state lists give 119 and 219 labels. |
| S003 | Independent AnalysisBase, the replacement framework and direct Python. Show the separate A/B ntuple leg and the common saved histogram endpoint. |
| S004 | One editable calibration diagram showing EtaJES and uncertainty groups shared across jet sizes and the radius-specific downstream stages. |
| S004a | Executed Python excerpts showing the native provider load and how both radius-specific corrections call shared EtaJES code. |
| S005 | The inclusive versus neutral-density input binding exposed by entry zero, jet zero. |
| S006 | Weighted small-R and selected large-R pT from both independently written histogram files, including the direct-minus-stock residual. [Main figure](../../figures/nominal-pt.png) |
| S007 | Full-input basket accounting for 26, 21 and 40 leaves. [Branch footprint](../../evidence/diagnostics/footprint.json) |
| S008 | Release-backed versus portable uncertainty calls on 2,000 events. [Stage timers](../../evidence/diagnostics/phase-001/portable-both.json) |
| S008a | The same seeded standard Gaussian recurs across ordinary uncertainty states. Show the small-R and combined elapsed times and explain the original negative-factor retry. [Matched original-stream comparison](../../evidence/timing/engineering/original-stream-pairs.json) |
| S008b | Small-R reuses only a raw NNJVT update with bitwise-identical inputs. Selection, SF choices and the event product still execute. [Matched original-stream comparison](../../evidence/timing/engineering/original-stream-pairs.json) |
| S008c | Pack the single-precision EtaJES cells exactly and load a single-radius subset on demand. Quantify the complete-job and memory differences. [Large-R loading repeat](../../evidence/diagnostics/loading-repeat/large.json) |
| Performance | Compare full PHYSLITE-to-histogram times for all three workflows and scopes, then compare just the two AnalysisBase framework legs for the 1.20 budget. The matched direct progression uses the original random stream. Each unresolved ratio keeps its own qualification. |
| Profile | Trace sampled joint uncertainty and small-R neural-network CPU costs in the installed workflow. Describe the separate wall-time and sampled CPU denominators. [Installed profile](../../profile-results.md) · [Native processing figure](../../figures/native-processing-time.png) |
| S009 | The actual PEP 723 invocation on an original file, with a local wheel and a single execution thread. |
| B01–B03 | All original pT, eta, phi and mass values in both collections, followed by raw NNJVT score, per-jet scale factor, effective weight and event product. [Small-R](../../figures/sr-coordinates.png) · [Large-R](../../figures/lr-coordinates.png) · [Weights](../../figures/sr-weights.png) |
| B04–B06 | Small-R derived energy where the release persists it, an all-state difference map, and representative varied momentum spectra with residuals. The original file has no large-R energy output. [State map](../../figures/all-state-agreement.png) · [Varied spectra](../../figures/representative-shifts.png) |
| B07 | Show original and direct selection and validity counts for every state of both collections, including the distinction between an absent and an out-of-validity decoration. [Selections and validity](../../figures/selection-validity.png) |

[State inventory](../../evidence/reference/jet-states.json) · [Independent full direct check](../../evidence/validation/full-direct/comparison.json) · [Input basket inventory](../../evidence/diagnostics/footprint.json)
