"""Render retained jet timing receipts as Markdown without rerunning a workflow."""

import argparse
from collections import defaultdict
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import re
import statistics
from urllib.parse import quote

CAMPAIGN = Path(__file__).resolve().parents[1]
PRODUCTION = CAMPAIGN / "evidence/timing/production/compact.json"
SCOPES = {"small": "Small-R", "large": "Large-R", "combined": "Combined"}
MODES = {"stored": "Read without corrections", "nominal": "Nominal calibration", "full": "Full systematics"}
LEGS = {"A": ("framework", "histogram", "total"), "B": ("framework", "histogram", "total"), "C": ("total",)}
LEG_NAMES = {"framework": "framework", "histogram": "ntuple read + histogram", "total": "total"}
FRAMEWORK_BUDGET = 1.20
WORKFLOW_GOAL = 10.0
MAX_CV = 0.05
MAX_DEVIATION = 0.10
WARMUP = 0
RETAINED = (1, 2, 3)
PROGRESS_KEY = re.compile(r"(anchor-)?(\d+)-(small|large|combined)-(stored|nominal|full)-([ABC])")


@dataclass(frozen=True)
class Series:
    values: tuple

    def __post_init__(self):
        if len(self.values) != len(RETAINED) or any(not math.isfinite(x) or x <= 0 for x in self.values):
            raise ValueError("Each timing series needs three positive finite retained wall times")

    @property
    def mean(self):
        return statistics.mean(self.values)

    @property
    def sd(self):
        return statistics.stdev(self.values)

    @property
    def passes(self):
        return self.sd / self.mean <= MAX_CV and median_deviation(self.values) <= MAX_DEVIATION

    def show(self):
        return f"{self.mean:.2f} ± {self.sd:.2f}"


@dataclass(frozen=True)
class Comparison:
    ratio: float
    paired: tuple
    threshold: float | None
    lower_passes: bool
    failures: tuple

    def meets(self, value):
        return value <= self.threshold if self.lower_passes else value >= self.threshold

    @property
    def straddles(self):
        return self.threshold is not None and len({self.meets(value) for value in self.paired}) > 1

    @property
    def qualified(self):
        return not self.failures and not self.straddles

    @property
    def threshold_pass(self):
        return self.meets(self.ratio) if self.threshold is not None and self.qualified else None

    def show(self, *, label_control=False):
        info = [f"{self.ratio:.2f}×"]
        if label_control:
            info.append("stock control")
        if self.failures:
            info.append(f"quality flagged ({', '.join(self.failures)})")
        if self.straddles:
            lo, hi = min(self.paired), max(self.paired)
            info.append(f"straddles {self.threshold:.2f}× ({lo:.2f}–{hi:.2f}×)")
        elif self.threshold_pass is not None:
            if self.lower_passes:
                decision = "within budget" if self.threshold_pass else "over budget"
            else:
                decision = "goal met" if self.threshold_pass else "below goal"
            info.append(f"{decision} ({self.threshold:.2f}×)")
        elif self.qualified and not label_control:
            info.append("quality passed")
        return " · ".join(info)


def median_deviation(values, median=None):
    if median is None:
        median = statistics.median(values)
    return max(abs(value - median) for value in values) / median


def close(actual, expected):
    return math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-12)


def verify_series(series, saved, label):
    if (tuple(saved["retained"]) != series.values or not close(saved["mean_s"], series.mean)
            or not close(saved["sample_sd_s"], series.sd)
            or not close(saved["sample_cv"], series.sd / series.mean)
            or not close(saved["max_median_deviation"], median_deviation(series.values))
            or saved["pass"] != series.passes):
        raise ValueError(f"Retained values, spread, or quality differ from the journal for {label}")


def measured_ratio(left, right, failures, threshold=None, *, lower_passes=False):
    return Comparison(
        left.mean / right.mean,
        tuple(a / b for a, b in zip(left.values, right.values, strict=True)),
        threshold,
        lower_passes,
        tuple(failures),
    )


def compare_cell(arms, drift, pair, mode):
    if pair == "AB":
        tested = {"A": ("framework",), "B": ("framework",)}
        numerator, denominator, endpoint = "B", "A", "framework"
        threshold = None if mode == "stored" else FRAMEWORK_BUDGET
    elif pair == "AC":
        tested = {"A": LEGS["A"], "C": LEGS["C"]}
        numerator, denominator, endpoint = "A", "C", "total"
        threshold = WORKFLOW_GOAL if mode == "full" else None
    else:
        tested = {"B": LEGS["B"], "C": LEGS["C"]}
        numerator, denominator, endpoint, threshold = "B", "C", "total", None
    failures = [f"{arm} {LEG_NAMES[leg]}" for arm, legs in tested.items()
                for leg in legs if not arms[arm][leg].passes]
    anchor_legs = ("framework",) if pair == "AB" else LEGS["A"]
    failures.extend(f"stock {LEG_NAMES[leg]} anchors" for leg in anchor_legs if not drift[leg]["pass"])
    return measured_ratio(arms[numerator][endpoint], arms[denominator][endpoint], failures,
                          threshold, lower_passes=pair == "AB")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_production(record):
    meta, summary = record["metadata"], record["summary"]
    if meta["cohort"] != "production":
        raise ValueError("The main compact archive must be the production cohort")
    expected = len(SCOPES) * len(MODES) * len(LEGS) * (1 + len(RETAINED)) + len(RETAINED) + 1
    if summary["completed"] != expected or summary["planned"] != expected:
        raise ValueError(f"Production grid is incomplete ({summary['completed']}/{summary['planned']} accepted jobs)")
    groups, anchors = defaultdict(dict), {}
    rows = record["observations"]
    if len(rows) != expected:
        raise ValueError("Compact archive does not contain exactly the accepted production grid")
    for row in rows:
        job, cls, wall = row["job"], row["classification"], row["wall_s"]
        scope, mode, arm, round_number = (job[key] for key in ("scope", "mode", "arm", "round"))
        key = scope, mode, arm
        if scope not in SCOPES or mode not in MODES or arm not in LEGS or set(wall) != set(LEGS[arm]):
            raise ValueError(f"Unexpected scope, mode, endpoint or timing leg in {job}")
        if any(not math.isfinite(value) or value <= 0 for value in wall.values()):
            raise ValueError(f"Invalid monotonic wall time in {job}")
        if arm != "C" and not close(wall["total"], wall["framework"] + wall["histogram"]):
            raise ValueError(f"Framework and histogram wall times do not sum to the endpoint in {job}")
        if job["anchor"]:
            if (cls != "anchor" or key != ("combined", "full", "A")
                    or round_number not in (*RETAINED, len(RETAINED) + 1) or round_number in anchors):
                raise ValueError(f"Unexpected production stock anchor in {job}")
            anchors[round_number] = wall
        else:
            wanted = "warmup" if round_number == WARMUP else "retained"
            if (round_number not in (WARMUP, *RETAINED) or cls != wanted
                    or job["warmup"] != (cls == "warmup") or round_number in groups[key]):
                raise ValueError(f"Duplicate round or unexpected timing classification in {job}")
            groups[key][round_number] = row
    cells = {}
    for scope in SCOPES:
        for mode in MODES:
            arms = cells[scope, mode] = {}
            for arm, legs in LEGS.items():
                series = arms[arm] = {}
                group = groups[scope, mode, arm]
                for leg in legs:
                    result = series[leg] = Series(tuple(group[n]["wall_s"][leg] for n in RETAINED))
                    saved = summary["quality"][scope][f"{mode}-{arm}"][leg]
                    verify_series(result, saved, f"{scope}/{mode}/{arm}/{leg}")
                    if saved["warmup_s"] != group[WARMUP]["wall_s"][leg]:
                        raise ValueError(f"Warm-up identity differs in {scope}/{mode}/{arm}/{leg}")
    drift = summary["stock_anchor_drift"]
    for leg in LEGS["A"]:
        samples = tuple(anchors[n][leg] for n in sorted(anchors))
        verify_anchor(drift[leg], samples, statistics.median(samples), "median_s")
    for (scope, mode), arms in cells.items():
        ratios = summary["ratios"][scope][mode]
        comparisons = {
            "B_over_A_framework": "AB",
            "A_over_C_end_to_end": "AC",
            "B_over_C_end_to_end": "BC",
        }
        for label, pair in comparisons.items():
            if not close(ratios[label], compare_cell(arms, drift, pair, mode).ratio):
                raise ValueError(f"Retained ratio differs from the journal for {scope}/{mode}/{pair}")
        if ratios["B_framework_budget_limit"] != FRAMEWORK_BUDGET:
            raise ValueError("The archived framework budget differs from the frozen threshold")
    return cells, drift, groups


def verify_anchor(saved, samples, median, median_key):
    deviation = median_deviation(samples, median)
    if (tuple(saved["wall_s"]) != samples or not close(saved[median_key], median)
            or not close(saved["max_median_deviation"], deviation)
            or saved["pass"] != (deviation <= MAX_DEVIATION)):
        raise ValueError("Stock anchor spread differs from the journal")


def recheck_key(summary, metadata):
    progress = []
    for key in summary["progress"]:
        found = PROGRESS_KEY.fullmatch(key)
        if not found:
            raise ValueError(f"Unexpected paired progress key {key}")
        anchor, round_number, scope, mode, arm = found.groups()
        progress.append((bool(anchor), int(round_number), scope, mode, arm))
    if metadata:
        key = metadata["scope"], metadata["mode"], metadata["pair"]
    else:
        cells = {(scope, mode) for _, _, scope, mode, _ in progress}
        if len(cells) != 1:
            raise ValueError("The paired receipt must identify exactly one scope and workload")
        scope, mode = cells.pop()
        pair = "".join(sorted({arm for anchor, _, _, _, arm in progress if not anchor}))
        key = scope, mode, pair
    scope, mode, pair = key
    if scope not in SCOPES or mode not in MODES or pair not in {"AB", "AC"} or (pair == "AB" and mode == "stored"):
        raise ValueError(f"Invalid recheck scope, mode or pair {key}")
    planned = {(False, rnd, scope, mode, arm) for rnd in (WARMUP, *RETAINED) for arm in pair}
    planned.update((True, rnd, scope, mode, "A") for rnd in (0, len(RETAINED) + 1))
    if len(planned) != summary["planned"] or not set(progress) <= planned or len(progress) != summary["completed"]:
        raise ValueError("Bounded recheck progress does not match the declared paired schedule")
    return key


def read_recheck(path, original_cells, original_drift):
    record = read_json(path)
    summary = record.get("summary", record)
    metadata = record.get("metadata", {}).get("timing_recheck")
    sibling = path.with_name("campaign.json")
    if metadata is None and path.name == "summary.json" and sibling.is_file():
        metadata = read_json(sibling).get("timing_recheck")
    scope, mode, pair = recheck_key(summary, metadata)
    original = compare_cell(original_cells[scope, mode], original_drift, pair, mode)
    if original.qualified:
        raise ValueError(f"Original {scope}/{mode}/{pair} comparison already qualified")
    if metadata and not close(metadata["original_ratio"]["ratio_of_retained_means"], original.ratio):
        raise ValueError("Recorded recheck origin differs from this production evidence")
    if summary["completed"] != summary["planned"]:
        return (scope, mode, pair), (path, None, None, None, summary)
    drift, saved = summary["stock_anchor_drift"], summary["comparison"]
    arms = {arm: {leg: Series(tuple(leg_data["retained"])) for leg, leg_data in series.items()}
            for arm, series in saved["quality"].items()}
    expected = {"A": ("framework",), "B": ("framework",)} if pair == "AB" else {"A": LEGS["A"], "C": LEGS["C"]}
    if set(arms) != set(expected) or any(set(arms[arm]) != set(legs) for arm, legs in expected.items()):
        raise ValueError("Bounded recheck timing legs differ from its pair")
    for arm, legs in arms.items():
        for leg, series in legs.items():
            verify_series(series, saved["quality"][arm][leg], f"recheck {scope}/{mode}/{arm}/{leg}")
    for leg in LEGS["A"]:
        samples = tuple(drift[leg]["wall_s"])
        if len(samples) != 2 or any(not math.isfinite(x) or x <= 0 for x in samples):
            raise ValueError("Each bounded stock bracket needs two positive anchor wall times")
        median = statistics.median(arms["A"][leg].values) if leg in arms["A"] else drift[leg]["retained_stock_median_s"]
        verify_anchor(drift[leg], samples, median, "retained_stock_median_s")
    result = compare_cell(arms, drift, pair, mode)
    name = "B_over_A_framework" if pair == "AB" else "A_over_C_end_to_end"
    if (saved["name"] != name or not close(saved["ratio_of_retained_means"], result.ratio)
            or len(saved["same_round_ratios"]) != len(result.paired)
            or any(not close(a, b) for a, b in zip(saved["same_round_ratios"], result.paired, strict=True))
            or saved["threshold"] != result.threshold or saved["retained_pairs_straddle"] != result.straddles
            or saved["ratio_qualified"] != result.qualified or summary["ratio_qualified"] != result.qualified
            or saved["quality_pass"] != (not result.failures) or summary["quality_pass"] != (not result.failures)
            or saved["threshold_pass"] != result.threshold_pass):
        raise ValueError("Bounded recheck comparison disagrees with its reported measurements")
    return (scope, mode, pair), (path, result, arms, drift, summary)


def markdown_link(path, base, label):
    try:
        relative = Path(os.path.relpath(path.resolve(), base)).as_posix()
    except ValueError:
        relative = path.resolve().as_uri()
    return f"[{label}]({quote(relative, safe='/:')})"


def table(headers, rows):
    return ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |",
            *("| " + " | ".join(row) + " |" for row in rows), ""]


def anchor_rows(drift):
    for leg, value in drift.items():
        wall = ", ".join(f"{item:.2f}" for item in value["wall_s"])
        comparison = value.get("retained_stock_median_s", value.get("median_s"))
        yield (LEG_NAMES[leg].capitalize(), wall, f"{comparison:.2f}",
               f"{value['max_median_deviation']:.1%}", "Pass" if value["pass"] else "Flagged")


def resources(groups):
    for scope in SCOPES:
        for arm in LEGS:
            work = [groups[scope, "full", arm][n].get("legs", {}) for n in RETAINED]
            expected = {"framework", "histogram"} if arm != "C" else {"columnar"}
            if any(set(sample) != expected for sample in work):
                continue
            cpu = statistics.mean(sum(leg["cpu_user_s"] + leg["cpu_sys_s"] for leg in row.values()) for row in work)
            rss = max(leg["peak_rss_kb"] for row in work for leg in row.values()) / 1024
            wait = [leg.get("cpu3_iowait_s") for row in work for leg in row.values()]
            io = f"{sum(wait) / len(work):.2f}" if all(value is not None for value in wait) else "Unavailable"
            yield (SCOPES[scope], arm, f"{cpu:.2f}", f"{rss:,.0f}", io)


def render(record, production, recheck_paths, base, *, show_resources=False):
    cells, drift, groups = read_production(record)
    rechecks = {}
    for path in recheck_paths:
        try:
            key, outcome = read_recheck(path, cells, drift)
        except (ValueError, KeyError, OSError) as error:
            raise ValueError(f"Invalid recheck receipt {path}: {error}") from error
        if key in rechecks:
            raise ValueError(f"Multiple bounded rechecks supplied for {'/'.join(key)}")
        rechecks[key] = outcome
    meta, summary = record["metadata"], record["summary"]
    first, last = meta["original"]["entry_interval"]
    lines = [
        "## Final PHYSLITE-to-histogram timing",
        "",
        f"Each job processed {last - first:,} events with one worker on CPU {meta['cpu']}. "
        "The controller interleaved fresh processes and excluded the first round. The three retained rounds "
        "give the arithmetic mean and sample standard deviation (SD). The monotonic wall clock includes process "
        "startup and output serialization. Filesystem and CVMFS caches could be warm. "
        f"The production journal records {summary['histogram_guards']} exact histogram checks. "
        + markdown_link(production, base, "Production timing receipts"),
        "",
        "A used stock AnalysisBase. B used the framework with CorrectionLib. Each ran a framework job that "
        "wrote an ntuple and a separate process that read it, filled the histogram, and saved it. "
        "C read the original PHYSLITE and saved the histogram in one direct Python job. The read-without-corrections "
        "control includes startup, reading and output work. In that control B also uses the stock workflow.",
        "",
        "### Wall times",
        "",
        "All values are in seconds. Total SD uses the summed framework and histogram times for each retained job.",
        "",
    ]
    lines += table(
        ("Scope", "Workload", "A framework", "A ntuple read + hist", "A total",
         "B framework", "B ntuple read + hist", "B total", "C direct"),
        ((SCOPES[scope], MODES[mode], *(arms[arm][leg].show() for arm, legs in LEGS.items() for leg in legs))
         for (scope, mode), arms in cells.items()),
    )
    lines += [
        "### Matched comparisons",
        "",
        "Each ratio divides retained means. The gate allows sample SD / mean up to 5% and an individual "
        "deviation from its cohort median up to 10%. Stock anchor deviations may be up to 10%. The B framework "
        "budget allows B/A up to 1.20× for nominal and full calibration. The full-systematics goal is A/C at least "
        "10×. Same-round ratios on both sides of a threshold leave that decision unresolved. Flagged values "
        "describe the observed runs. A B/A decision uses both framework legs and the stock framework anchors. "
        "An end-to-end comparison uses all measured legs of its two paths and the stock anchors.",
        "",
    ]
    lines += table(
        ("Scope", "Workload", "B/A framework", "A/C workflow", "B/C workflow"),
        ((SCOPES[scope], MODES[mode], *(compare_cell(arms, drift, pair, mode).show(label_control=pair == "AB" and mode == "stored")
                                      for pair in ("AB", "AC", "BC")))
         for (scope, mode), arms in cells.items()),
    )
    lines += [
        "### Stock anchors",
        "",
        "The production controller repeated the combined stock full-systematics job between rounds and after "
        "the last round. The drift check compares each anchor with the median of the anchors for the same leg.",
        "",
    ]
    lines += table(("Leg", "Anchor seconds", "Anchor median (s)", "Maximum deviation", "Drift check"), anchor_rows(drift))
    if rechecks:
        lines += [
            "### Bounded paired rechecks",
            "",
            "Each recheck uses its own retained runs and its own stock brackets. The brackets are compared with "
            "the median of retained stock runs in that recheck. A qualified recheck supplies the decision for "
            "its pair. Original cohort values remain in the tables above.",
            "",
        ]
        for (scope, mode, pair), (path, result, arms, brackets, status) in rechecks.items():
            title = f"{SCOPES[scope]} · {MODES[mode]} · {pair[0]}/{pair[1]}"
            lines.extend((f"#### {title}", ""))
            source = markdown_link(path, base, "Paired recheck receipt")
            if result is None:
                lines.extend((f"{status['completed']}/{status['planned']} jobs accepted. Decision pending. {source}", ""))
                continue
            values = ", ".join(f"{x:.2f}×" for x in result.paired)
            lines.extend((f"{result.show()}. Same-round ratios were {values}. {source}", ""))
            lines += table(("Path", "Leg", "Mean ± SD (s)"),
                           ((arm, LEG_NAMES[leg], series.show()) for arm, legs in arms.items()
                            for leg, series in legs.items()))
            lines += table(("Leg", "Bracket seconds", "Retained stock median (s)", "Maximum deviation", "Drift check"),
                           anchor_rows(brackets))
    lines += [
        "### Combined job compared with two standalone jobs",
        "",
        "For each path and workload, the standalone sum adds the small-R and large-R totals from the same "
        "round. Its SD describes those three sums. The ratio divides the measured combined mean by the "
        "standalone-sum mean.",
        "",
    ]
    combined = []
    for mode, label in MODES.items():
        for arm in LEGS:
            small, large, both = (cells[scope, mode][arm]["total"] for scope in SCOPES)
            summed = Series(tuple(a + b for a, b in zip(small.values, large.values, strict=True)))
            flagged = [SCOPES[scope] for scope, series in zip(SCOPES, (small, large, both), strict=True)
                       if not series.passes]
            if not summed.passes:
                flagged.append("standalone sums")
            if not drift["total"]["pass"]:
                flagged.append("stock total anchors")
            quality = ", ".join(flagged) if flagged else "Pass"
            combined.append((label, arm, both.show(), summed.show(), f"{both.mean / summed.mean:.2f}×", quality))
    lines += table(("Workload", "Path", "Combined (s)", "Small-R + Large-R (s)", "Combined / sum", "Quality flags"), combined)
    if show_resources:
        lines += [
            "### Full-systematics process resources",
            "",
            "CPU time sums user and system time across each job's legs and averages the retained jobs. "
            "Peak RSS is the largest process peak across legs and rounds. CPU-slot I/O wait is a guest "
            "counter observed during the legs.",
            "",
        ]
        resource_rows = list(resources(groups))
        if resource_rows:
            lines += table(("Scope", "Path", "Mean process CPU (s)", "Maximum peak RSS (MiB)",
                            "Mean guest CPU-slot I/O wait (s)"), resource_rows)
        else:
            lines.extend(("The supplied archive has no complete per-leg resource observations for these jobs.", ""))
    return "\n".join(lines).rstrip("\n") + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--production", type=Path, default=PRODUCTION, help="Completed production compact.json")
    parser.add_argument("--recheck-summary", action="append", type=Path, default=[],
                        help="Bounded recheck summary.json or compact archive. Repeat per scope, workload and pair")
    parser.add_argument("--output", type=Path, help="New Markdown file. Omit to print")
    parser.add_argument("--resources", action="store_true", help="Include recorded full-systematics CPU and memory")
    args = parser.parse_args()
    base = args.output.resolve().parent if args.output else CAMPAIGN
    try:
        report = render(read_json(args.production), args.production, args.recheck_summary, base,
                        show_resources=args.resources)
        if args.output:
            with args.output.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(report)
        else:
            print(report, end="")
    except (OSError, ValueError, KeyError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
