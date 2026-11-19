# /// script
# requires-python = ">=3.14,<3.15"
# dependencies = ["numpy==2.5.5", "matplotlib==3.11.2"]
# ///
"""Plot the saved AnalysisBase and direct full-systematics histogram arrays."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

folder = Path(__file__).resolve().parent
evidence = folder.parent / "evidence" / "histograms"

with np.load(folder.parent / "evidence/final/installed-histograms.npz", allow_pickle=False) as direct:
    fig, axes = plt.subplots(2, 2, figsize=(11.2, 5.7), sharex="col",
                             gridspec_kw={"height_ratios": [3.4, 1], "hspace": 0.06})
    for i, (prefix, name, title) in enumerate((
            ("sr", "small", "Small-R jets · NNJVT weights"),
            ("lr", "large", "Large-R jets · kinematic selection"))):
        ax, diff = axes[:, i]
        with np.load(evidence / f"stock-{name}.npz", allow_pickle=False) as stock:
            states = stock[f"{prefix}_states"]
            np.testing.assert_array_equal(states, direct[f"{prefix}_states"])
            index = states.tolist().index("NOSYS")
            edges = stock["edges"]
            a = stock[f"{prefix}_sumw"][:, index]
            c = direct[f"{prefix}_sumw"][:, index]
            assert len(a) == len(edges) + 1
            np.testing.assert_array_equal(stock["edges"], direct["edges"])
            centers = 0.5 * (edges[1:] + edges[:-1])
            ax.stairs(a[1:-1], edges, color="#24668a", linewidth=2.0, label="AnalysisBase")
            ax.plot(centers[c[1:-1] > 0], c[1:-1][c[1:-1] > 0], linestyle="none",
                    marker="o", markersize=5, markerfacecolor="white", markeredgecolor="#a13e18",
                    label="Direct CorrectionLib")
            ax.set_yscale("log")
            ax.set_ylim(bottom=0.7)
            ax.set_title(title, loc="left", fontsize=13)
            ax.set_ylabel("Weighted jets / bin" if prefix == "sr" else "Jets / bin")
            ax.legend(frameon=False, fontsize=9)
            diff.axhline(0, color="#777777", linewidth=0.8)
            diff.scatter(centers, (c-a)[1:-1], color="#a13e18", s=15)
            diff.set_ylim(-1, 1)
            diff.set_yticks([-1, 0, 1])
            diff.set_ylabel("C − A")
            diff.set_xlabel("Jet transverse momentum [GeV]")
            diff.set_xscale("symlog", linthresh=40)
            diff.set_xlim(0, 3000)
            diff.set_xticks([0, 20, 40, 100, 300, 1000, 3000],
                            labels=["0", "20", "40", "100", "300", "1000", "3000"])
            ax.grid(axis="y", alpha=0.18)
            for panel in (ax, diff):
                panel.spines[["top", "right"]].set_visible(False)
    fig.subplots_adjust(left=0.09, right=0.98, bottom=0.14, top=0.87, wspace=0.26)
    fig.suptitle("Nominal calibration in 20,000 original PHYSLITE events", fontsize=16)
    fig.savefig(folder / "nominal-pt.png", dpi=160, facecolor="white")
    plt.close(fig)
