# /// script
# requires-python = ">=3.14,<3.15"
# dependencies = ["numpy==2.5.5", "matplotlib==3.11.2"]
# ///
"""Plot retained full-file wall times with the original spread and drift flags."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

folder = Path(__file__).resolve().parent
record = json.loads((folder.parent / "evidence/timing/production/compact.json").read_text())
scopes = ("small", "large", "combined")
arms = {"A": ("AnalysisBase", "#28678a"), "B": ("Framework + CorrectionLib", "#7a9396"),
        "C": ("Direct Python", "#aa4821")}
fig, ax = plt.subplots(figsize=(9.2, 4.9))
offsets = (-0.24, 0.0, 0.24)
largest = 0
for offset, (arm, (label, color)) in zip(offsets, arms.items(), strict=True):
    for index, scope in enumerate(scopes):
        observations = [row["wall_s"]["total"] for row in record["observations"]
                        if row["classification"] == "retained" and row["job"]["scope"] == scope
                        and row["job"]["arm"] == arm and row["job"]["mode"] == "full"]
        if len(observations) != 3:
            raise ValueError(f"Expected all three retained {scope}/{arm} values")
        x = index + offset
        mean = np.mean(observations)
        largest = max(largest, max(observations))
        ax.bar(x, mean, 0.205, color=color, alpha=0.83, label=label if index == 0 else None)
        ax.scatter(x + np.linspace(-0.031, 0.031, 3), observations, s=14,
                   facecolor="white", edgecolor=color, linewidth=1, zorder=4)
        ax.annotate(f"{mean:.1f}", (x, max(observations)), xytext=(0, 4),
                    textcoords="offset points", ha="center", va="bottom", fontsize=9)
labels = []
for scope, title in zip(scopes, ("Small-R", "Large-R", "Combined"), strict=True):
    passed = record["summary"]["ratios"][scope]["full"]["quality_pass"]
    labels.append(title if passed else title + " *")
ax.set_xticks(range(3), labels)
ax.set_ylim(0, largest * 1.17)
ax.set_ylabel("Seconds per 20,000-event job")
ax.spines[["right", "top"]].set_visible(False)
ax.set_axisbelow(True)
ax.grid(axis="y", alpha=0.2)
fig.suptitle("Time from PHYSLITE to the saved full-systematics histograms", x=0.085, ha="left")
fig.legend(*ax.get_legend_handles_labels(), ncol=3, loc="upper left",
           bbox_to_anchor=(0.075, 0.93), frameon=False)
note = "Points show individual jobs. Bars show their arithmetic mean."
if any("*" in label for label in labels):
    note += "  * At least one spread or stock-drift check failed."
fig.text(0.085, 0.035, note, fontsize=9)
fig.subplots_adjust(left=0.085, right=0.985, bottom=0.16, top=0.80)
fig.savefig(folder / "full-workflow-time.png", dpi=155)
