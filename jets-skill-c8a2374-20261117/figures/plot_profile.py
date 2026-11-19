# /// script
# requires-python = ">=3.14,<3.15"
# dependencies = ["matplotlib==3.11.2"]
# ///
"""Show disjoint native stack owners on the scale of one full combined file."""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


folder = Path(__file__).resolve().parent
evidence = folder.parent / "evidence"
owners = {
    "Shared JES/JER/JMS uncertainties": {"joint_jes_jer_jms"},
    "Small-R NNJVT update": {"small_nnjvt_update"},
    "Other NNJVT and event weights": {"small_nnjvt_scale_factor", "small_nnjvt_selection", "small_event_scale_factor"},
    "Large-R forward-folded JMR": {"large_jmr_forward_fold"},
    "Array operations and histogram filling": {"array_operations", "histogram_fill"},
    "CorrectionLib with no tool on stack": {"correctionlib_unattributed"},
    "Unresolved stacks": {"unresolved"},
}


def seconds_per_file(path):
    record = json.loads((path / "recording.json").read_text())
    if not record["passed"] or record["scope"] != "both" or record["events_per_pass"] != 20_000:
        raise ValueError(f"Incompatible full-file profile in {path}")
    measured_passes = record["repeat"] - 1
    with (path / "owners.tsv").open() as table:
        times = {row["owner"]: int(row["period_ns"]) / (1e9 * measured_passes)
                 for row in csv.DictReader(table, delimiter="\t")}
    rows = {name: sum(times.get(key, 0) for key in group) for name, group in owners.items()}
    remaining = times.keys() - set().union(*owners.values())
    rows["Other tool and runtime groups"] = sum(times[key] for key in remaining)
    return rows


baseline = seconds_per_file(evidence / "diagnostics/native-portable-baseline")
final = seconds_per_file(evidence / "final/native")
fig, ax = plt.subplots(figsize=(9.7, 5.7))
positions = list(range(len(baseline)))
for offset, values, marker, color, label in (
    (-0.13, baseline, "o", "#28678a", "Portable baseline"),
    (0.13, final, "s", "#a04824", "Delivered workflow"),
):
    y = [i + offset for i in positions]
    ax.hlines(y, 0, list(values.values()), color=color, alpha=0.6, lw=2)
    ax.scatter(list(values.values()), y, marker=marker, color=color, s=28, label=label, zorder=3)
ax.set_yticks(positions, list(baseline))
ax.invert_yaxis()
ax.set_xlim(left=0)
ax.set_xlabel("Sampled processing CPU seconds per 20,000-event file")
ax.grid(axis="x", alpha=0.18)
ax.spines[["top", "right", "left"]].set_visible(False)
ax.tick_params(axis="y", length=0, pad=7)
fig.suptitle("Where the combined jet workflow spends native CPU time", x=0.045, ha="left", fontsize=16)
fig.legend(*ax.get_legend_handles_labels(), frameon=False, ncol=2, loc="upper left", bbox_to_anchor=(0.038, 0.922))
fig.text(0.045, 0.018, "Each stack has one owner. Rates use complete repeated passes after initialization. Both profiles reproduced the stock histogram.", fontsize=9)
fig.subplots_adjust(left=0.322, right=0.98, top=0.8, bottom=0.15)
fig.savefig(folder / "native-processing-time.png", dpi=145)
