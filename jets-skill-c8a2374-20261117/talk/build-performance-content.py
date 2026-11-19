"""Build editable-deck timing content and a reader summary from accepted receipts."""

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path, PurePosixPath
import re
import sys


REPORT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPORT / "figures"))
from summarize_timings import (  # noqa: E402
    FRAMEWORK_BUDGET, MODES, PRODUCTION, RETAINED, SCOPES, WORKFLOW_GOAL,
    Series, close, compare_cell, measured_ratio, read_json, read_production, read_recheck, verify_series,
)


PROGRESSION_SCOPES = {"small": "small", "large": "large", "combined": "both"}
PROGRESSION_ARMS = ("faithful", "packed", "final")
PROGRESSION_PAIRS = (("faithful", "packed"), ("packed", "final"), ("faithful", "final"))


def source(path):
    path = path.resolve()
    return {"path": path.relative_to(REPORT).as_posix() if path.is_relative_to(REPORT) else str(path),
            "sha256": sha256(path.read_bytes()).hexdigest()}


def series_data(series):
    return {"mean_s": series.mean, "sample_sd_s": series.sd, "retained_s": series.values,
            "spread_pass": series.passes}


def arm_data(arms):
    return {arm: {name: series_data(series) for name, series in legs.items()} for arm, legs in arms.items()}


def comparison_data(result):
    return {"ratio_of_means": result.ratio, "same_round_ratios": result.paired, "threshold": result.threshold,
            "qualified": result.qualified, "threshold_pass": result.threshold_pass,
            "straddles": result.straddles, "quality_flags": result.failures}


def read_progression(path, provenance_path, production, groups):
    summary, provenance = read_json(path), read_json(provenance_path)
    metadata = production["metadata"]
    arms = set(provenance["arms"])
    scope_names = set(PROGRESSION_SCOPES.values())
    omission = summary["faithful_omission"]
    branches = summary["matching_physical_branch_sha256"]
    if (provenance["input"] != metadata["original"] or provenance["events"] != 20_000
            or provenance["cpu"] != metadata["cpu"] or provenance["threads"] != 1
            or provenance["rounds"] != 1 + len(RETAINED)
            or set(provenance["scopes"]) != scope_names or set(summary["results"]) != scope_names
            or set(branches) != scope_names or not summary["all_histograms_exact"]
            or arms not in (set(PROGRESSION_ARMS), {"packed", "final"})
            or omission != provenance["faithful_omission"]
            or bool(omission) != ("faithful" not in arms)):
        raise ValueError("Progression lacks matched input, complete scope coverage or exact stock proof")
    expected = {(round_no, scope, arm) for round_no in range(1, provenance["rounds"] + 1)
                for scope in scope_names for arm in arms}
    schedule = provenance["schedule"]
    if len(schedule) != len(expected) or set(map(tuple, schedule)) != expected:
        raise ValueError("Progression schedule is incomplete or includes duplicate cells")
    final = provenance["arms"]["final"]
    identities = metadata["identity_sha256"]
    for receipt in (final["wheel"], final["visible_script"]):
        matches = {digest for filename, digest in identities.items()
                   if PurePosixPath(filename).name == PurePosixPath(receipt["path"]).name}
        if matches != {receipt["sha256"]}:
            raise ValueError("Progression final artifact differs from the production workflow")
    results = {}
    for scope, name in PROGRESSION_SCOPES.items():
        observed = {row["input_visit_counters"]["input_branch_sha256"]
                    for row in groups[scope, "full", "C"].values()}
        if not re.fullmatch(r"[0-9a-f]{64}", branches[name]) or observed != {branches[name]}:
            raise ValueError(f"Progression and full production branch requests differ for {scope}")
        cell = summary["results"][name]
        if set(cell["arms"]) != arms:
            raise ValueError(f"Progression results omit a scheduled arm for {scope}")
        series = {}
        for arm in PROGRESSION_ARMS:
            if arm not in arms:
                continue
            wall = cell["arms"][arm]["wall"]
            row = series[arm] = Series(tuple(wall["retained"]))
            verify_series(row, wall, f"progression {scope}/{arm}")
            if not math.isfinite(wall["warmup_s"]) or wall["warmup_s"] <= 0:
                raise ValueError(f"Invalid progression warmup for {scope}/{arm}")
        ratios = {}
        for left, right in PROGRESSION_PAIRS:
            if not {left, right} <= arms:
                continue
            key = f"{left}_over_{right}"
            saved = cell["speedup_ratios"][key]
            result = measured_ratio(series[left], series[right], [arm for arm in (left, right) if not series[arm].passes])
            if (not close(result.ratio, saved["ratio_of_retained_means"])
                    or len(saved["same_round_wall_ratios"]) != len(result.paired)
                    or any(not close(a, b) for a, b in zip(result.paired, saved["same_round_wall_ratios"], strict=True))
                    or saved["qualified_for_spread"] != result.qualified):
                raise ValueError(f"Progression ratio differs from retained times for {scope}/{key}")
            ratios[key] = comparison_data(result)
        if set(ratios) != set(cell["speedup_ratios"]):
            raise ValueError(f"Unexpected progression ratio for {scope}")
        results[scope] = {"wall": {arm: series_data(row) for arm, row in series.items()}, "comparisons": ratios,
                          "input_branch_sha256": branches[name]}
    return {"faithful_omission": omission, "scopes": results}


def decision(original, recheck, pair):
    if original.qualified:
        effective, origin = original, "production"
    elif recheck is not None and recheck["comparison"] and recheck["comparison"]["qualified"]:
        passes = recheck["comparison"]["threshold_pass"]
        return {"source": "recheck", "status": threshold_status(pair, passes),
                "comparison": recheck["comparison"]}
    else:
        effective, origin = None, None
    return {"source": origin, "status": threshold_status(pair, effective.threshold_pass) if effective else "unresolved",
            "comparison": comparison_data(effective) if effective else None}


def threshold_status(pair, passes):
    if passes is None:
        return "qualified"
    if pair == "AB":
        return "within_budget" if passes else "over_budget"
    return "goal_met" if passes else "below_goal"


def render(production_path, recheck_paths, progression_path, provenance_path, figure):
    production = read_json(production_path)
    cells, drift, groups = read_production(production)
    meta, summary = production["metadata"], production["summary"]
    if (meta["cpu"] != 3 or meta["original"]["entry_interval"] != [0, 20_000]
            or not meta["columnar_matched_read"] or summary["histogram_guards"] <= 0):
        raise ValueError("Production does not identify the matched full-file timing and histogram checks")
    production_source = source(production_path)
    rechecks = {}
    for path in recheck_paths:
        key, (_, result, arms, brackets, status) = read_recheck(path, cells, drift)
        if key in rechecks:
            raise ValueError(f"Multiple bounded rechecks for {'/'.join(key)}")
        rechecks[key] = {
            "source": source(path), "completed": status["completed"], "planned": status["planned"],
            "comparison": comparison_data(result) if result else None,
            "wall": arm_data(arms) if arms else None, "stock_brackets": brackets,
        }
    scopes = {}
    for scope in SCOPES:
        ratios = {}
        for mode, pair in (("full", "AC"), ("nominal", "AB"), ("full", "AB")):
            original = compare_cell(cells[scope, mode], drift, pair, mode)
            recheck = rechecks.get((scope, mode, pair))
            ratios[f"{mode}_{pair}"] = {"production": comparison_data(original), "recheck": recheck,
                                         "decision": decision(original, recheck, pair)}
        scopes[scope] = {"full_wall": arm_data(cells[scope, "full"]), "comparisons": ratios}

    progress = None
    if progression_path is not None:
        progress = read_progression(progression_path, provenance_path, production, groups)
        progress["summary_source"] = source(progression_path)
        progress["provenance_source"] = source(provenance_path)
    reader = {
        "schema": 1, "production": production_source, "campaign": production.get("campaign"),
        "events": 20_000, "cpu": meta["cpu"], "input_sha256": meta["original"]["sha256"],
        "histogram_guards": summary["histogram_guards"], "jobs_accepted": summary["completed"], "stock_anchors": drift,
        "scopes": scopes, "same_stream_progression": progress,
        "bounded_rechecks": [{"scope": scope, "mode": mode, "pair": pair, **result}
                             for (scope, mode, pair), result in sorted(rechecks.items())],
    }
    return {"slides": slides_for(reader, cells, drift, figure)}, reader


def recheck_notes(reader, pair, modes):
    notes = []
    for item in reader["bounded_rechecks"]:
        if item["pair"] != pair or item["mode"] not in modes:
            continue
        title = f"{SCOPES[item['scope']]} {MODES[item['mode']].lower()}"
        result = item["comparison"]
        if result is None:
            observation = f"{item['completed']}/{item['planned']} jobs accepted, decision pending"
        else:
            status = threshold_status(pair, result["threshold_pass"]) if result["qualified"] else "unresolved"
            observation = f"{result['ratio_of_means']:.2f}×, {status.replace('_', ' ')}"
        notes.append(f"Separate paired recheck for {title} measured {observation}. {item['source']['path']}")
    return " ".join(notes)


def slides_for(reader, cells, drift, figure):
    full = reader["scopes"]
    production = reader["production"]["path"]
    ac = {scope: compare_cell(cells[scope, "full"], drift, "AC", "full") for scope in SCOPES}
    conclusions = []
    for scope, name in SCOPES.items():
        cell = full[scope]["comparisons"]["full_AC"]
        latest = (cell["recheck"] or {}).get("comparison") or cell["production"]
        qualifier = " · unresolved" if cell["decision"]["status"] == "unresolved" else ""
        conclusions.append(f"{name} {latest['ratio_of_means']:.2f}×{qualifier}")
    takeaway = "Full A/C after checks    " + "    |    ".join(conclusions)
    flags = " ".join(f"{SCOPES[scope]} {row.show()}." for scope, row in ac.items())
    slides = [{
        "title": "From PHYSLITE to the full-systematics histograms",
        "figure": figure,
        "takeaway": takeaway,
        "notes": (
            f"Each job reads the same {reader['events']:,} events with one analysis thread. "
            "The bars and points describe production jobs. Each bar is the mean of three retained rounds after one warmup. "
            "A and B include the framework ntuple and the separate histogram job. C runs the delivered direct script "
            f"through histogram output. A/C is the ratio of means. The full-workflow goal is {WORKFLOW_GOAL:g}×. "
            f"{flags} {recheck_notes(reader, 'AC', {'full'})} Source {production}."
        ),
    }]
    rows = [["Scope", "Nominal B/A", "Full B/A"]]
    framework_notes = []
    for scope, name in SCOPES.items():
        row = [name]
        for mode in ("nominal", "full"):
            outcome = full[scope]["comparisons"][f"{mode}_AB"]["decision"]
            original = compare_cell(cells[scope, mode], drift, "AB", mode)
            recheck = full[scope]["comparisons"][f"{mode}_AB"]["recheck"]
            latest = (recheck or {}).get("comparison")
            ratio = latest["ratio_of_means"] if latest else original.ratio
            verdict = {"within_budget": "within", "over_budget": "over", "unresolved": "unresolved"}[outcome["status"]]
            suffix = " (recheck)" if latest else ""
            row.append(f"{ratio:.2f}× · {verdict}{suffix}")
            framework_notes.append(f"{name} {mode} production {original.show()}.")
        rows.append(row)
    slides.append({
        "title": "Framework wall time against the 1.20× budget",
        "rows": rows,
        "takeaway": "B/A compares framework jobs through ntuple output. The first round is excluded.",
        "notes": (
            f"The budget allows CorrectionLib framework B up to {FRAMEWORK_BUDGET:.2f}× stock A for nominal calibration "
            "and full systematics. Each ratio divides the framework-only retained means. Stock anchors and endpoint "
            "spread must qualify, and same-round ratios that straddle the budget leave the decision unresolved. "
            f"{' '.join(framework_notes)} {recheck_notes(reader, 'AB', {'nominal', 'full'})} Source {production}."
        ),
    })
    progress = reader["same_stream_progression"]
    if progress is not None:
        slides.append(progression_slide(progress))
    return slides


def progression_slide(progress):
    rows = [["Scope", "Faithful (s)", "Packed (s)", "Selected (s)", "Faithful/selected"]]
    for scope, name in SCOPES.items():
        cell = progress["scopes"][scope]
        row = [name]
        for arm in PROGRESSION_ARMS:
            stats = cell["wall"].get(arm)
            if stats is None:
                row.append("Unavailable")
            else:
                flag = "" if stats["spread_pass"] else "*"
                row.append(f"{stats['mean_s']:.2f} ± {stats['sample_sd_s']:.2f}{flag}")
        ratio = cell["comparisons"].get("faithful_over_final")
        row.append("Unavailable" if ratio is None else
                   f"{ratio['ratio_of_means']:.2f}×" + ("" if ratio["qualified"] else "*"))
        rows.append(row)
    omission = progress["faithful_omission"]
    return {
        "title": "What changed within the direct workflow",
        "rows": rows,
        "takeaway": "Same branch requests and stock-exact histograms. Wall time includes startup and output.",
        "notes": (
            "This independent progression compares end-to-end full-systematics direct commands. "
            "Each arm is a fresh process and each scope uses the same original events and branch-set digest. "
            "The histogram is exact against stock for each job. The displayed means and sample SD use three "
            "retained runs after one warmup. An asterisk marks a spread failure. This progression compares "
            "bundled configurations. It cannot assign an isolated speedup to one mechanism. "
            f"{'Faithful runtime omitted. ' + omission + ' ' if omission else ''}"
            f"Sources {progress['summary_source']['path']} and {progress['provenance_source']['path']}."
        ),
    }


def write_json(path, value):
    with path.open("x", encoding="ascii", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--production", type=Path, default=PRODUCTION, help="Completed production compact archive")
    parser.add_argument("--recheck-summary", type=Path, action="append", default=[], help="Optional paired receipt, repeatable")
    parser.add_argument("--progression", type=Path, help="Same-stream progression summary.json")
    parser.add_argument("--progression-provenance", type=Path, help="Defaults to progression's sibling provenance.json")
    parser.add_argument("--figure", default="full-workflow-time.png", help="Existing chart name under report/figures")
    parser.add_argument("--output", required=True, type=Path, help="New slides JSON for build-deck.ps1 -TimingFile")
    parser.add_argument("--reader-output", type=Path, help="New reader summary JSON, defaults to stdout")
    args = parser.parse_args()
    if args.progression_provenance and not args.progression:
        parser.error("--progression-provenance requires --progression")
    if args.figure != Path(args.figure).name or not args.figure.lower().endswith(".png"):
        parser.error("--figure must be the filename of a PNG within the figures directory")
    lineage = (args.progression_provenance or args.progression.with_name("provenance.json")) if args.progression else None
    try:
        if args.output.exists() or (args.reader_output and
                                    (args.reader_output.exists() or args.reader_output.resolve() == args.output.resolve())):
            raise ValueError("Choose fresh and distinct output paths")
        slides, reader = render(args.production, args.recheck_summary, args.progression, lineage, args.figure)
        write_json(args.output, slides)
        if args.reader_output:
            write_json(args.reader_output, reader)
        else:
            print(json.dumps(reader, separators=(",", ":"), allow_nan=False))
    except (OSError, ValueError, KeyError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
