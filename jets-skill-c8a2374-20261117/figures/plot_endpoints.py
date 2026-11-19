# /// script
# requires-python = ">=3.14,<3.15"
# dependencies = ["numpy==2.5.5", "matplotlib==3.11.2"]
# ///
"""Render independently accumulated full-sample AnalysisBase and portable C distributions."""
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
import matplotlib.pyplot as plt
import numpy as np

folder = Path(__file__).resolve().parent
evidence = folder.parent / "evidence"
data_path = evidence / "final" / "distributions.npz"
data = np.load(data_path, allow_pickle=False)
kinematics = {"pt": "Transverse momentum [GeV]", "eta": "Pseudorapidity",
              "phi": "Azimuth [rad]", "mass": "Jet mass [GeV]"}
small_weights = {"nnjvt_score": "NNJVT score", "nnjvt_sf": "Raw jet scale factor",
                 "histogram_weight": "Effective jet weight", "event_sf": "Event scale factor"}
names = {"sr": "Small-R", "lr": "Large-R"}


def panel(fig, layout, prefix, var, label, state=0):
    slot = layout.subgridspec(2, 1, height_ratios=[3.2, 1], hspace=0.07)
    top = fig.add_subplot(slot[0])
    bottom = fig.add_subplot(slot[1], sharex=top)
    k = f"{prefix}_{var}"
    a = data[k + "_stock_counts"][state]
    c = data[k + "_direct_counts"][state]
    edges = data[k + "_edges"]
    centers = (edges[:-1] + edges[1:]) / 2
    top.stairs(a[1:-1], edges, color="#28678a", linewidth=1.8, label="AnalysisBase")
    mask = c[1:-1] > 0
    top.plot(centers[mask], c[1:-1][mask], "o", markerfacecolor="white",
             markeredgecolor="#aa4821", markersize=3.8, label="Direct CorrectionLib")
    if var == "phi":
        top.set_ylim(bottom=0)
    else:
        top.set_yscale("log")
        top.set_ylim(bottom=0.7)
    top.set_title(label, loc="left", fontsize=11)
    top.set_ylabel("Events / bin" if var == "event_sf" else "Jets / bin")
    top.grid(axis="y", alpha=0.16)
    top.tick_params(labelbottom=False)
    bottom.axhline(0, color="#6b7377", linewidth=0.8)
    delta = (c-a)[1:-1]
    bottom.scatter(centers, delta, s=12, color="#aa4821")
    bound = max(1.0, max(abs(delta)) * 1.15)
    bottom.set_ylim(-bound, bound)
    bottom.set_yticks([-bound, 0, bound] if bound == 1 else [0])
    bottom.set_ylabel("C − A")
    if var in ("pt", "mass", "energy"):
        bottom.set_xscale("symlog", linthresh=5 if var == "mass" else 30)
        ticks = ([-100, -10, 0, 10, 100, 1000] if var == "mass" else
                 [v for v in (0, 20, 100, 500, 3000, 10000) if v <= edges[-1]])
        bottom.set_xticks(ticks, labels=[str(v) for v in ticks])
    bottom.set_xlim(edges[0], edges[-1])
    for ax in (top, bottom):
        ax.spines[["right", "top"]].set_visible(False)
    return top


def plot_group(prefix, fields, title, filename):
    fig = plt.figure(figsize=(10.4, 7.8))
    grid = fig.add_gridspec(2, 2, left=0.09, right=0.98, bottom=0.07,
                            top=0.88, hspace=0.44, wspace=0.26)
    for slot, (var, label) in zip(grid, fields.items()):
        ax = panel(fig, slot, prefix, var, label)
    fig.suptitle(title, fontsize=16, x=0.09, ha="left")
    fig.legend(*ax.get_legend_handles_labels(), frameon=False, ncol=2,
               loc="upper left", bbox_to_anchor=(0.08, 0.952))
    fig.savefig(folder / filename, dpi=145)
    plt.close(fig)


for prefix, name in names.items():
    plot_group(prefix, kinematics, f"{name} jet coordinates · nominal calibration",
               f"{prefix}-coordinates.png")
plot_group("sr", small_weights, "Small-R NNJVT and weights · nominal calibration",
           "sr-weights.png")

if "sr_energy_states" in data:
    fig = plt.figure(figsize=(9.6, 4.9))
    grid = fig.add_gridspec(1, 2, left=0.09, right=0.955, bottom=0.12,
                            top=0.80, wspace=0.27)
    states = data["sr_energy_states"]
    stock_counts = data["sr_energy_stock_counts"]
    varied = int(1 + np.argmax(abs(stock_counts[1:] - stock_counts[0]).sum(axis=1)))
    for slot, index in zip(grid, (0, varied)):
        name = str(states[index]).replace("JET_", "").replace("__1", " ")
        ax = panel(fig, slot, "sr", "energy", "Nominal" if index == 0 else name, index)
        fig.axes[-1].set_xlabel("Jet energy [GeV]")
    fig.suptitle("Small-R jet energy from the calibrated four-vector", x=0.09, ha="left")
    fig.legend(*ax.get_legend_handles_labels(), frameon=False, ncol=2, loc="upper left",
               bbox_to_anchor=(0.08, 0.935))
    fig.savefig(folder / "sr-energy.png", dpi=145)
    plt.close(fig)

fig, axes = plt.subplots(2, 1, figsize=(10.5, 5.8), gridspec_kw={"height_ratios":[2,1]})
for ax, (prefix, name) in zip(axes, names.items()):
    variables = kinematics | (small_weights if prefix == "sr" else {})
    keys = [f"{prefix}_{field}" for field in variables]
    # The mask reports either an object-level discrepancy or a saved bin-count discrepancy.
    flags = np.array([(data[k + "_exact_mismatches"] != 0) |
                      np.any(data[k + "_count_residual"] != 0, axis=1) for k in keys])
    flags = flags.astype(int)
    if prefix == "sr" and "sr_energy_states" in data:
        variables = variables | {"energy": "Jet energy [GeV]"}
        available = dict(zip(data["sr_energy_states"],
                             (data["sr_energy_exact_mismatches"] != 0) |
                             np.any(data["sr_energy_count_residual"] != 0, axis=1)))
        flags = np.vstack([flags, [int(available.get(state, -1)) for state in data["sr_states"]]])
    ax.imshow(flags, aspect="auto", interpolation="nearest", origin="upper",
              cmap=ListedColormap(["#adb5b9", "#dceee7", "#a33a1f"]), vmin=-1, vmax=1,
              extent=[-0.5, flags.shape[1]-0.5, flags.shape[0]-0.5, -0.5])
    ax.set_yticks(np.arange(len(variables)), labels=list(variables.values()))
    ax.set_xlim(-0.5, flags.shape[1]-0.5)
    ax.set_title(f"{name}  ·  {flags.shape[1]} release states  ·  {(flags > 0).sum()} cells with differences",
                 loc="left", fontsize=11)
    ax.set_xlabel("Systematic-state index in release order (0 is nominal)")
fig.tight_layout(rect=(0, 0.065, 1, 1))
fig.legend(handles=[Patch(color="#dceee7", label="Exact agreement"),
                    Patch(color="#adb5b9", label="No independent energy branch for weight-only states"),
                    Patch(color="#a33a1f", label="Difference")],
           loc="lower center", ncol=3, frameon=False, fontsize=9)
fig.savefig(folder / "all-state-agreement.png", dpi=145)
plt.close(fig)

metadata = json.loads(data_path.with_name("metadata.json").read_text())
decisions = {
    "sr": [("jesJerValidity", "JES/JER valid", "4294967295"), ("nnjvtPass", "NNJVT pass", "1"),
           ("jvtSelection", "JVT selection", "1"), ("jvtValidity", "JVT SF valid", "4294967295"),
           ("isJvtHS", "Hard-scatter label", "1")],
    "lr": [("jesJERJMSValidity", "JES/JER/JMS valid", "4294967295"), ("jmrValidity", "JMR valid", "4294967295"),
           ("selectPtEta", "Kinematic pass", "4294967295"), ("selectMass", "Mass pass", "4294967295")],
}
fig, axes = plt.subplots(2, 2, figsize=(10.8, 5.8), height_ratios=[3.1, 1], sharex="col")
for col, (prefix, fields) in enumerate(decisions.items()):
    rows = metadata["collections"][prefix]["states"]
    positions = np.arange(len(rows))
    maximum = np.zeros(len(rows), dtype=int)
    for (key, label, accepted), color in zip(fields, ("#17668b", "#9c4832", "#407651", "#694d82", "#8d631f")):
        values = [row["codes"][key] for row in rows]
        for i, item in enumerate(values):
            a, c = item["stock"], item["direct"]
            residual = max((abs(c.get(k, 0) - a.get(k, 0)) for k in a.keys() | c.keys()), default=0)
            maximum[i] = max(maximum[i], residual)
        for side in ("stock", "direct"):
            fractions = [100 * v[side].get(accepted, 0) / sum(v[side].values()) for v in values]
            if side == "stock":
                axes[0, col].plot(positions, fractions, lw=1.5, color=color, label=label)
            else:
                axes[0, col].scatter(positions, fractions, s=4, facecolors="none", edgecolors=color, linewidths=0.5)
    axes[0, col].legend(frameon=False, ncol=2, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, 1.21))
    axes[0, col].set_title(names[prefix], loc="left", pad=44)
    axes[0, col].set_ylim(-4, 105)
    axes[0, col].set_ylabel("Fraction of original jets [%]")
    axes[1, col].scatter(positions, maximum, s=6, color="#884421")
    axes[1, col].set_ylim(-0.6, max(1.0, 1.1 * maximum.max()))
    axes[1, col].set_ylabel("Max |C − A|\n[jet count]")
    axes[1, col].set_xlabel("Systematic-state index (0 is nominal)")
    for ax in axes[:, col]:
        ax.grid(axis="y", alpha=0.17)
        ax.spines[["top", "right"]].set_visible(False)
fig.suptitle("Selection and validity across the complete state inventory", x=0.085, ha="left", fontsize=15)
fig.text(0.085, 0.012, "Lines show AnalysisBase. Circles show direct CorrectionLib. Residuals include all saved codes, including absence.", fontsize=9)
fig.subplots_adjust(left=0.085, right=0.985, bottom=0.15, top=0.74, hspace=0.12, wspace=0.25)
fig.savefig(folder / "selection-validity.png", dpi=145)
plt.close(fig)

fig = plt.figure(figsize=(10.4, 7.8))
grid = fig.add_gridspec(2, 2, left=0.09, right=0.98, bottom=0.07,
                        top=0.86, hspace=0.55, wspace=0.26)
for row, prefix in enumerate(names):
    a = data[f"{prefix}_pt_stock_counts"]
    distance = abs(a[1:]-a[0]).sum(axis=1)
    ordered = np.argsort(distance, kind="stable")+1
    for col, idx in enumerate((ordered[(len(ordered)-1)//2], ordered[-1])):
        state = str(data[prefix+"_states"][idx]).replace("JET_", "").replace("__1", " ")
        ax = panel(fig, grid[row, col], prefix, "pt", f"{names[prefix]}  ·  {state}", int(idx))
        ax.set_xlabel("")
        fig.axes[-1].set_xlabel("Jet transverse momentum [GeV]")
fig.suptitle("Momentum agreement for representative systematic variations", fontsize=15, x=0.09, ha="left")
fig.legend(*ax.get_legend_handles_labels(), frameon=False, ncol=2, loc="upper left",
           bbox_to_anchor=(0.08, 0.95))
fig.savefig(folder / "representative-shifts.png", dpi=145)
plt.close(fig)
