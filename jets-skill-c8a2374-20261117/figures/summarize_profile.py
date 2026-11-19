"""Render the installed jet demo's native, phase and Python profile receipts."""

import argparse
import csv
from datetime import datetime
from hashlib import sha256 as hash_sha256
import json
import os
from collections import Counter
from pathlib import Path, PurePosixPath
import pstats
import re
import shlex
from urllib.parse import quote


SCOPES = {"both": "Combined", "small": "Small-R", "large": "Large-R"}
COLLECTIONS = {"both": {"sr", "lr"}, "small": {"sr"}, "large": {"lr"}}
TOOLS = {"shared", "small-R", "large-R"}
PROVIDER_LABELS = {
    "joint_jes_jer_jms": "JES/JER/JMS uncertainties",
    "eta_jes": "EtaJES",
    "event_inputs": "Event inputs",
    "pileup_truth_labelling": "Pileup truth labelling",
    "small_pileup": "Pileup calibration",
    "small_gsc": "Global sequential calibration",
    "small_nnjvt_update": "NNJVT update",
    "small_nnjvt_selection": "NNJVT selection",
    "small_nnjvt_scale_factor": "NNJVT scale factor",
    "small_event_scale_factor": "Event scale factor",
    "large_jms": "Nominal JMS",
    "large_jmr_forward_fold": "Forward-folded JMR",
    "large_selections": "Large-R selections",
    "histogram_fill": "Histogram fill",
    "decompression": "Decompression",
    "array_operations": "Array operations",
    "correctionlib_unattributed": "CorrectionLib without a named tool",
    "provider_unattributed": "Jet provider without a named tool",
    "python_or_other_native": "Python or other native work",
    "unresolved": "Unresolved stack owner",
}
GROUP_LABELS = {
    "setup": "Calibration setup",
    "io": "Open, branch selection, read and decode",
    "workflow": "Python workflow and dispatch",
    "tool": "CorrectionLib tool calls",
    "transport": "Transport bindings",
    "histogram": "Histogram operations",
    "output": "Output and runtime audit",
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    digest = hash_sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def table_rows(path, decoded):
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    for row in rows:
        for key in row:
            if key in {"samples", "period_ns"}:
                row[key] = int(row[key])
            elif key.startswith("percent_"):
                row[key] = float(row[key])
    if rows != decoded:
        raise ValueError(f"Decoded JSON and TSV differ in {path}")
    return rows


def read_native(directory, recording_path):
    native = load(directory / "summary.json")
    record = load(recording_path)
    if (not native["passed"] or not record["passed"] or record["scope"] != "both"
            or native["measurement"] != record["measurement"]
            or native["artifact"] != record["wheel"]):
        raise ValueError("The decoder receipt must cover a successful combined recording of the supplied wheel")
    measure = record["measurement"]
    if (measure["required_floor_s"] < 60 or measure["worker_cpu_floor_s"] < measure["required_floor_s"]
            or record["calibration_cpu"] != 3 or record["perf_collector_cpu"] != 3
            or record["calibration_threads"] != 1 or record["machine"]["event"] != "cpu-clock:u"):
        raise ValueError("Native recording lacks the required worker CPU floor or single-CPU proof")
    exact = record["histogram"]["exact_stock_fields"]
    repeat = record["repeat"]
    visits = record["pass_ends"]
    expected = [(i, repeat, record["events_per_pass"]) for i in range(1, repeat + 1)]
    if (not exact or not all(exact.values()) or repeat < 2 or record["events_per_pass"] != 20_000
            or record["event_visits"] != repeat * record["events_per_pass"]
            or [(row["pass"], row["of"], row["events"]) for row in visits] != expected
            or len({row["objects"] for row in visits}) != 1 or set(record["unique_objects"]) != COLLECTIONS["both"]
            or record["object_visits"] != {key: value * repeat for key, value in record["unique_objects"].items()}
            or visits[0]["controller_monotonic_ns"] != measure["start_ns"]
            or visits[-1]["controller_monotonic_ns"] != measure["end_ns"]):
        raise ValueError("Native recording did not demonstrate deterministic complete-file visits")
    native["owners"] = table_rows(directory / "owners.tsv", native["owners"])
    for mode in ("self", "inclusive"):
        native[mode] = table_rows(directory / f"{mode}.tsv", native[mode])
        table_rows(directory / f"within_owner_{mode}.tsv", [
            {"owner": owner, **row} for owner, table in native["within_owner"].items() for row in table[mode]
        ])
    periods = native["denominator_period_ns"]
    samples = native["samples"]["processing"]
    if (periods <= 0 or samples <= 0 or sum(row["period_ns"] for row in native["owners"]) != periods
            or sum(row["samples"] for row in native["owners"]) != samples
            or sum(row["period_ns"] for row in native["self"]) != periods
            or sum(native["resolved_frame_depth_histogram"].values()) != samples
            or any(sum(row["period_ns"] for row in native["within_owner"][owner["owner"]]["self"])
                   != owner["period_ns"] for owner in native["owners"])):
        raise ValueError("Disjoint owners, self times or decoded sample counts fail to reconcile")
    return record, native


def read_phases(summary_path, provenance_path, record):
    phases = load(summary_path)
    if set(phases) != SCOPES.keys():
        raise ValueError("Expected the combined, small-R and large-R phase diagnostics")
    for scope, phase in phases.items():
        total = (phase["startup_through_visible_cli_entry_ns"] + phase["teardown_after_visible_cli_ns"]
                 + sum(phase["exclusive_groups_inside_visible_cli_ns"].values())
                 + phase["remaining_phase_overhead_ns"])
        objects = {prefix: record["unique_objects"][prefix] for prefix in COLLECTIONS[scope]}
        if (not phase["exact_stock_histogram"] or not phase["tools"] or total != phase["external_wall_ns"]
                or phase["objects"] != objects):
            raise ValueError(f"Phase totals, source object counts or stock proof disagree for {scope}")
    provenance = load(provenance_path) if provenance_path.is_file() else None
    if provenance is not None and (
        provenance["wheel"]["sha256"] != record["wheel"]["sha256"]
        or provenance["demo"]["sha256"] != record["demo"]["sha256"]
        or provenance["selected_defaults"] != record["shipped_defaults"]
        or provenance["events"] != record["events_per_pass"] or provenance["original"]["bytes"] != record["original"]["bytes"]
        or provenance["repeat"] != 1 or provenance["cpu"] != 3 or provenance["threads"] != 1
    ):
        raise ValueError("Phase provenance does not match the installed wheel, policy or native workload")
    return phases, provenance


def read_python(directory, phases, provenance, record):
    summary = load(directory / "summary.json")
    source = load(directory / "provenance.json")
    command = load(directory / "command.json")
    process = load(directory / "visible.json")
    comparison = load(directory / "histogram-comparison.json")
    audit = summary["source_and_runtime_audit"]
    original = source["original"]
    combined = phases["both"]
    runtime = load(directory / "library-maps.json")
    histogram = directory / "histograms.npz"
    if (provenance is None or source["demo"] != record["demo"] or source["wheel"] != provenance["wheel"]
            or source["wheel"]["native"] != record["wheel"]["native"]
            or any(source["bundle"][key] != provenance["bundle"][key] for key in ("path", "sha256"))
            or source["selected_defaults"] != record["shipped_defaults"]
            or source["original"] != provenance["original"] or original["entry_interval"] != [0, 20_000]
            or [source[key] for key in ("scope", "mode", "events", "passes", "cpu", "threads")]
            != ["both", "full", 20_000, 1, 3, 1]):
        raise ValueError("Python profile does not identify the selected installed combined full workflow")
    if (len(command) != 10 or command[1:7] != ["-m", "cProfile", "-o", summary["pstats"]["path"],
                                             record["demo"]["path"], record["original"]["path"]]
            or PurePosixPath(command[7]).name != histogram.name or command[8:] != ["--events", "20000"]):
        raise ValueError("Python profile command differs from the sealed visible invocation")
    if (process["argv"] != ["taskset", "-c", "3", *command] or process["exit"] != 0
            or process["threads_seen"] != [1] or process["cpus_seen"] != ["3"] or not process["source_mapping_observed"]
            or audit["objects"] != record["unique_objects"]
            or any(audit[key] != combined[key] for key in ("branch_sha256", "compact_payload",
                                                          "nnjvt_reuse", "unsigned_pair_reuse"))
            or runtime != audit["runtime_maps"] or runtime != record["audit"]
            or f"({original['tfile_uuid']})" not in (directory / "visible.log").read_text(encoding="utf-8")):
        raise ValueError("Python profile lacks the matched source, branch, scope or runtime mapping proof")
    checks = record["histogram"]["exact_stock_fields"]
    if (not summary["passed"] or not summary["exact_stock_histogram"] or not checks or not all(checks.values())
            or comparison["exact_fields"] != checks or sha256(histogram) != comparison["sha256"]
            or source["stock"]["histogram"]["sha256"] != record["stock_histogram"]["sha256"]):
        raise ValueError("Python profile is missing the independent exact stock histogram guard")
    return summary, process, original


def read_overhead(directory, stage, record_path, record, phases, provenance):
    diagnostic = load(directory / "diagnostic.json")
    process = load(directory / "application.json")
    commands = load(directory / "command.json")
    profiled = load(record_path.with_name("command.json"))
    profiled = profiled[profiled.index("--") + 1:]
    unprofiled = commands["unprofiled_argv"]
    resolved = load(stage.parent / "resolved.json")
    if (provenance is None or record["repeat"] != 10 or diagnostic["repeat"] != 10
            or diagnostic["events_per_pass"] != record["events_per_pass"] or not diagnostic["passed"]
            or profiled != [resolved["installed_python"], record["demo"]["path"], record["original"]["path"],
                            record["histogram"]["path"], "-n", "10"]
            or commands["recorded_visible_argv"] != profiled
            or len(unprofiled) != len(profiled) or unprofiled[:3] != profiled[:3] or unprofiled[4:] != profiled[4:]
            or unprofiled[3] == profiled[3] or PurePosixPath(unprofiled[3]).name != "histogram.npz"
            or diagnostic["profile_recording"] != str(PurePosixPath(profiled[3]).with_name("recording.json"))
            or diagnostic["process_receipt"] != str(PurePosixPath(unprofiled[3]).with_name("application.json"))
            or diagnostic["input_branch_sha256"] != phases["both"]["branch_sha256"]):
        raise ValueError("Unprofiled comparison does not identify the exact recorded ten-pass installed workload")
    exact = record["histogram"]["exact_stock_fields"]
    runtime = load(directory / "library-maps.json")
    if (process["argv"] != ["taskset", "-c", "3", *unprofiled] or process["exit"] != 0
            or process["threads_seen"] != [1] or process["cpus_seen"] != ["3"] or not process["source_mapping_observed"]
            or runtime != diagnostic["physically_mapped_libraries"] or runtime != record["audit"]
            or process["wall_s"] != diagnostic["wall_s"] or diagnostic["stock_exact_fields"] != exact
            or diagnostic["profiled_exact_fields"] != exact
            or sha256(directory / "histogram.npz") != diagnostic["histogram_sha256"]):
        raise ValueError("Unprofiled process receipt lacks the exact endpoint or one-worker runtime proof")
    controller_command = shlex.split((stage / "command.txt").read_text(encoding="utf-8"))
    if ((stage / "exit-code").read_text().strip() != "0"
            or controller_command[:3] != ["taskset", "-c", "3"]
            or controller_command[-3:] != ["record-profile", "--scope", "both"]
            or len(controller_command) != 9 or controller_command[4] != "tools/qualify_shipment.py"
            or PurePosixPath(controller_command[5]).name != "specification.json"
            or resolved["output"] != str(PurePosixPath(profiled[3]).parents[1])
            or resolved["wheel"] != record["wheel"]["path"] or resolved["demo"] != record["demo"]["path"]
            or resolved["bundle_manifest_sha256"] != provenance["bundle"]["sha256"]
            or resolved["original"] != {**provenance["original"], "resolved_path": record["original"]["path"]}
            or not resolved["unprofiled_overhead"] or resolved["profile_repeats"] != record["repeat"]):
        raise ValueError("Native recorder stage does not belong to the matched comparison")
    times = []
    for name in ("started.utc", "ended.utc"):
        whole, nanos = (stage / name).read_text().strip().removesuffix("Z").split(".")
        second = int(datetime.fromisoformat(whole + "+00:00").timestamp())
        times.append(second * 10**9 + int(nanos.ljust(9, "0")))
    lower = record["pass_ends"][-1]["wall_from_launch_s"]
    upper = (times[1] - times[0]) / 1e9
    wall = process["wall_s"]
    if not 0 < lower <= upper or wall <= 0:
        raise ValueError("Native stage timestamps or observed process walls are inconsistent")
    return lower, upper, wall


def table(lines, headings, rows):
    lines.append("| " + " | ".join(headings) + " |")
    lines.append("| " + " | ".join("---" for _ in headings) + " |")
    lines.extend("| " + " | ".join(str(value) for value in row) + " |" for row in rows)
    lines.append("")


def code(text):
    return "`" + str(text).replace("|", r"\|").replace("`", "′") + "`"


def symbol(text):
    previous = None
    while text != previous:
        previous = text
        text = re.sub(r"<[^<>]+>", "<>", text)
    text = text.replace("<>", "<…>")
    return code(text if len(text) <= 112 else text[:111] + "…")


def seconds(ns, passes=1):
    return f"{ns / (passes * 1e9):.3f}"


def percent(value):
    return f"{value:.2f}%"


def label(owner):
    return PROVIDER_LABELS.get(owner, owner.replace("_", " "))


def link(title, path, output):
    try:
        target = os.path.relpath(path.resolve(), output.resolve().parent)
    except ValueError:  # Separate drives on Windows.
        target = str(path.resolve())
    return f"[{title}]({quote(target.replace(os.sep, '/'), safe='/:')})"


def report_native(lines, record, native, limit):
    passes = record["repeat"] - 1
    measure = record["measurement"]
    samples = native["samples"]
    count = samples["processing"]
    total = native["denominator_period_ns"]
    depth = native["resolved_frame_depth_histogram"]
    unresolved = samples.get("unresolved_leaf", 0)
    method = record["machine"]["event"]
    sample_ms = record["machine"]["period_ns"] / 1e6
    lines.extend([
        "## Native processing profile", "",
        f"The {SCOPES[record['scope']]} run made {record['repeat']} complete visits to the original "
        f"{record['events_per_pass']:,}-event PHYSLITE file, containing {record['unique_objects']['sr']:,} small-R "
        f"and {record['unique_objects']['lr']:,} large-R jets. The final saved histogram matched stock in all "
        f"{len(record['histogram']['exact_stock_fields'])} fields. The worker and collector ran on CPU 3 with one "
        "calibration thread.", "",
        f"The sampled interval runs from observed completion of pass 1 through pass {record['repeat']}. "
        f"It covers {measure['wall_s']:.2f} s of wall time and a conservative worker CPU floor of "
        f"{measure['worker_cpu_floor_s']:.2f} s against the required {measure['required_floor_s']:.0f} s. "
        f"Across those {passes} visits this is {measure['wall_s'] / passes:.3f} s wall and at least "
        f"{measure['worker_cpu_floor_s'] / passes:.3f} s worker CPU per file. "
        f"The CPU floor uses the tick-adjusted interior snapshots recorded by the controller.", "",
        f"Perf used {code(method)} with DWARF stacks and a configured {sample_ms:g} ms period. The denominator is "
        f"{count:,} accepted user-space sample "
        f"periods summing to {seconds(total)} s, or {seconds(total, passes)} sampled CPU s per file. "
        f"The decoder used {native['sample_cpu_basis']} and sample weights {native['sample_period_basis']}. "
        f"The repeated processing window and the fresh-start phase diagnostic answer different measurements.", "",
    ])
    combined = Counter()
    for row in native["owners"]:
        combined[row["scope"]] += row["period_ns"]
    quality = [
        ("Samples outside the processing window", f"{samples.get('out_of_processing_window', 0):,}"),
        ("Accepted samples with a recorded CPU", f"{samples.get('with_sample_cpu', 0):,} / {count:,}"),
        ("Samples from an unexpected worker or CPU", f"{samples.get('unexpected_cpu_or_worker', 0):,}"),
        ("Samples with an unresolved leaf symbol", f"{unresolved:,} / {count:,} ({percent(100 * unresolved / count)})"),
        ("Samples with no resolved frame", f"{depth.get('0', 0):,} / {count:,}"),
        ("Samples with an inline leaf and no resolved module", f"{samples.get('inline_leaf_dso_unresolved', 0):,}"),
    ]
    for name in ("parse_defects", "physical_parse_defects"):
        defects = native[name]
        quality.append(("Inline decoder defects" if name == "parse_defects" else "Physical decoder defects",
                        ", ".join(f"{key.replace('_', ' ')} {value:,}" for key, value in sorted(defects.items())) or "0"))
    table(lines, ("Stack coverage", "Observed"), quality)

    lines.extend([
        "### Disjoint tool and runtime ownership", "",
        "Each sample is assigned to the nearest identifiable provider stage using physical frames and then inline "
        "symbols. A stage can own a sample whose leaf function is unresolved. The shared uncertainty owner pools "
        "both radii in the combined recording. The instrumented table below gives the measured calls by radius, "
        "including calls whose native stacks did not receive a named sample owner.", "",
    ])
    table(lines, ("Owner scope", "Sampled CPU s/file", "Share"),
          ((scope, seconds(ns, passes), percent(100 * ns / total)) for scope, ns in combined.most_common()))
    owners = sorted(native["owners"], key=lambda row: -row["period_ns"])
    table(lines, ("Executing tool or runtime group", "Scope", "Samples", "Sampled CPU s/file", "Share"),
          ((label(row["owner"]), row["scope"], f"{row['samples']:,}", seconds(row["period_ns"], passes),
            percent(row["percent_of_window"])) for row in owners))

    lines.extend([
        "### Hottest native routines", "",
        "Self time assigns each accepted sample to its logical leaf. Inclusive time counts a routine once per "
        "stack, including samples spent in callees. Inclusive rows overlap. The tables are sorted independently "
        "by measured weight. Full demangled symbols are available in the linked TSVs.", "",
    ])
    for mode in ("self", "inclusive"):
        rows = sorted(native[mode], key=lambda row: -row["period_ns"])[:limit]
        table(lines, (f"Routine by {mode} time", "Module", "Sampled CPU s/file", "Window share"),
              ((symbol(row["symbol"]), code(row["dso"].rsplit("/", 1)[-1]), seconds(row["period_ns"], passes),
                percent(row["percent_of_window"])) for row in rows))
    lines.extend(["### Routines within each named tool", "",
                  "For each sampled tool the table shows the two heaviest self and inclusive routines. "
                  "The final two columns use the tool’s owned samples and the whole processing window respectively.", ""])
    table(lines, ("Tool", "Scope", "Basis", "Routine", "Module", "Tool share", "Window share"), (
        (label(owner["owner"]), owner["scope"], mode, symbol(row["symbol"]), code(row["dso"].rsplit("/", 1)[-1]),
         percent(row["percent_of_owner"]), percent(row["percent_of_window"]))
        for owner in owners if owner["scope"] in TOOLS
        for mode in ("self", "inclusive")
        for row in sorted(native["within_owner"][owner["owner"]][mode], key=lambda row: -row["period_ns"])[:2]
    ))


def report_phases(lines, phases, provenance):
    lines.extend([
        "## Instrumented fresh-file phases", "",
        "These single-pass diagnostics include interpreter startup and the saved histogram. Wall phases use "
        "exclusive hooks to avoid double counting nested calls. CPU time is the worker process clock, sampled "
        "before writing its diagnostic receipt. Tool rows include actual CorrectionLib dispatch plus any "
        "instrumented callees. Rows count tool inputs across calls, chunks and systematics. These measurements "
        "are separate from retained timing runs.", "",
    ])
    if provenance is None:
        lines.extend(["Phase provenance was unavailable. The table uses the supplied phase summaries without a cross-receipt wheel check.", ""])
    rows = []
    for scope, name in SCOPES.items():
        row = phases[scope]
        compact = row["compact_payload"]
        rows.append((name, seconds(row["external_wall_ns"]), seconds(row["worker_cpu_ns"]),
                     f"{compact['bytes']:,}" if compact else "Canonical", "Active" if row["nnjvt_reuse"] else "Inactive"))
    table(lines, ("Scope", "20,000-event wall s", "Worker CPU s", "Payload bytes if projected", "NNJVT reuse"), rows)
    groups = set().union(*(row["exclusive_groups_inside_visible_cli_ns"] for row in phases.values()))
    ordered_groups = [*filter(groups.__contains__, GROUP_LABELS), *sorted(groups - GROUP_LABELS.keys())]
    table(lines, ("Exclusive wall phase", *SCOPES.values()), [
        ("Startup through CLI entry", *(seconds(row["startup_through_visible_cli_entry_ns"]) for row in phases.values())),
        *((GROUP_LABELS.get(group, group), *(seconds(row["exclusive_groups_inside_visible_cli_ns"].get(group, 0))
                                           for row in phases.values())) for group in ordered_groups),
        ("Teardown after CLI", *(seconds(row["teardown_after_visible_cli_ns"]) for row in phases.values())),
        ("Remaining phase overhead", *(seconds(row["remaining_phase_overhead_ns"]) for row in phases.values())),
        ("External wall total", *(seconds(row["external_wall_ns"]) for row in phases.values())),
    ])
    table(lines, ("Startup or remainder detail", *SCOPES.values()), [
        (title, *(seconds(row["startup_detail"][key]) for row in phases.values())) for key, title in (
            ("worker_bootstrap_before_visible_ns", "Worker bootstrap before visible script"),
            ("visible_import_to_cli_ns", "Visible import through CLI entry"),
            ("compiler_runtime_inside_visible_import_ns", "Compiler runtime within visible import"),
        )
    ] + [("Diagnostic receipt and other wall time outside the observed worker interval",
          *(seconds(row["diagnostic_report_and_uninstrumented_process_remainder_ns"]) for row in phases.values()))])
    lines.extend(["The detail rows break out portions of startup and remainder already included in the exclusive wall table.", ""])

    for scope, name in SCOPES.items():
        lines.extend([f"### {name} correction calls", ""])
        rows = sorted(phases[scope]["tools"].items(), key=lambda row: (-row[1]["wall_ns"], row[0]))
        table(lines, ("Correction node", "Calls", "Rows", "Wall s", "Worker CPU s"),
              ((code(tool), f"{values['calls']:,}", f"{values['rows']:,}", seconds(values["wall_ns"]),
                seconds(values["cpu_ns"])) for tool, values in rows))


def profile_location(row):
    filename = PurePosixPath(row["file"]).name
    return code(f"{filename}:{row['line']} {row['name']}" if filename != "~" else row["name"])


def profile_times(row):
    return (f"{row['calls']:,}", f"{row['self_s']:.3f}", f"{row['cumulative_s']:.3f}")


def report_python(lines, summary, process, original, raw):
    lines.extend([
        "## Installed combined Python call profile", "",
        f"One cProfile pass ran the delivered full-systematics defaults on the original "
        f"{original['entry_interval'][1]:,}-event file. It physically mapped the source and installed "
        f"runtime on CPU 3 with one analysis thread. Every saved histogram field matched independent stock. "
        f"The process took {process['wall_s']:.3f} s wall. The profile recorded "
        f"{summary['total_self_s']:.3f} s across {summary['total_calls']:,} calls. "
        "Self time excludes recorded callees and can include native work in a Python binding. Cumulative "
        "rows include callees and can overlap. This diagnostic sits outside retained timing.", "",
    ])
    groups = [summary["top_by_self"], summary["top_by_cumulative"],
              *(group["by_self"] for group in summary["focus"].values())]
    compact = {(row["file"], row["line"], row["name"]): row for group in groups for row in group}
    selected = [
        ("CorrectionLib dispatch", "/correctionlib/highlevel.py", "_evaluate"),
        ("NumPy flatten in CorrectionLib input dispatch", "~", "<method 'flatten' of 'numpy.ndarray' objects>"),
        ("NumPy astype", "~", "<method 'astype' of 'numpy.ndarray' objects>"),
        ("NumPy where dispatch hook", "/numpy/_core/multiarray.py", "where"),
        ("Status conversion", "/jets_demo.py", "status_bits"),
        ("Per-chunk evaluation", "/jets_demo.py", "evaluate_chunk"),
        ("NNJVT selection", "/jets_demo.py", "small_jvt_selection"),
        ("NNJVT update orchestration", "/jets_demo.py", "evaluate"),
        ("NNJVT scale-factor orchestration", "/jets_demo.py", "small_sf"),
        ("Histogram façade", "/hist/basehist.py", "fill"),
        ("Histogram fill implementation", "/boost_histogram/histogram.py", "fill"),
        ("JSON decoder across all callers", "/json/decoder.py", "raw_decode"),
        ("Native CorrectionLib parse and construction", "~", "<built-in method correctionlib._core.from_string>"),
    ]
    matched = [(label, row) for label, suffix, name in selected for row in compact.values()
               if row["file"].endswith(suffix) and row["name"] == name]
    table(lines, ("Measured function", "Function", "Calls", "Self s", "Cumulative s"),
          ((label, profile_location(row), *profile_times(row)) for label, row in matched))
    lines.extend(["Each caller row measures a direct call edge and contributes to the function totals above. "
                  "The table shows up to three callers per selected function. The NumPy `where` row measures "
                  "its Python dispatch hook, with no separately identified native kernel time.", ""])
    caller_labels = {"NumPy flatten in CorrectionLib input dispatch", "NumPy astype", "NumPy where dispatch hook",
                     "Status conversion", "NNJVT update orchestration", "Histogram façade"}
    table(lines, ("Invoked function", "Direct caller", "Calls", "Self s", "Cumulative s"),
          ((label, profile_location(edge), *profile_times(edge)) for label, row in matched
           if label in caller_labels for edge in row["callers"][:3]))
    if raw is not None:
        report_python_raw(lines, raw, summary)
    else:
        lines.extend(["The compact receipt shows the total JSON decode and the native parser as separate rows. "
                      "Caller-specific attribution through plugin preparation is available from the receipt-hashed "
                      "raw pstats with `--python-pstats`.", ""])


def report_python_raw(lines, raw, summary):
    receipt = summary["pstats"]
    if raw.stat().st_size != receipt["bytes"] or sha256(raw) != receipt["sha256"]:
        raise ValueError("Raw pstats differs from the archived profile receipt")
    stats = pstats.Stats(str(raw))
    if stats.total_calls != summary["total_calls"]:
        raise ValueError("Raw pstats and compact caller totals disagree")
    prepare, = [key for key in stats.stats if key[0].endswith("/correctionlib/plugins.py") and key[2] == "prepare"]
    loads, = [key for key in stats.stats if key[0].endswith("/json/__init__.py") and key[2] == "loads"]
    input_flatten, = [key for key in stats.stats if key[0].endswith("/atlas_jet_demo/inputs.py") and key[2] == "flatten"]
    prepare_cost = stats.stats[prepare][3]
    prepare_loads = stats.stats[loads][4][prepare][3]
    load_total = stats.stats[loads][3]
    flat_calls, flat_self, flat_total = stats.stats[input_flatten][1:4]
    lines.extend([
        f"The direct `plugins.prepare → json.loads` call took {prepare_loads:.3f} s of "
        f"{load_total:.3f} s across all `json.loads` calls ({percent(100 * prepare_loads / load_total)}). "
        f"Plugin preparation took {prepare_cost:.3f} s including Python parsing and the validation walk. "
        "Native parsing and construction are measured separately above.", "",
        f"The visible input helper `atlas_jet_demo.inputs.flatten` made {flat_calls:,} calls "
        f"({flat_self:.3f} s self, {flat_total:.3f} s cumulative). The NumPy flatten row above measures "
        "calls directly under CorrectionLib's high-level dispatcher.", "",
    ])


def report_overhead(lines, bounds, repeat):
    lower, upper, plain = bounds
    crosses_zero = " The interval spans zero." if lower <= plain <= upper else ""
    lines.extend(["## Matched native sampling overhead diagnostic", "",
                  f"The recorded and unprofiled commands used the same installed script, runtime libraries, "
                  f"physical branches and {repeat} visits to the original file. Both saved histograms matched "
                  "independent stock in every field. The recorded process wall is bounded by the last pass "
                  "receipt and the duration of the enclosing recorder stage.", ""])
    table(lines, ("Boundary", "Wall s"), [
        ("Profiled lower bound through last pass receipt", f"{lower:.3f}"),
        ("Profiled upper bound through recorder stage exit", f"{upper:.3f}"),
        ("Unprofiled worker process start to exit", f"{plain:.3f}"),
    ])
    lines.extend([
        f"Profiled minus unprofiled wall for this pair lies between {lower - plain:+.2f} and "
        f"{upper - plain:+.2f} s. The lower bound ends before output and teardown. The upper bound includes "
        f"controller metadata and checks.{crosses_zero} Run-to-run variation also contributes to the observed "
        "difference. This diagnostic pair sits outside formal timing.", "",
    ])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("native_directory", type=Path, help="Directory containing decoded summary.json and its five TSVs")
    parser.add_argument("phase_summary", type=Path, help="Aggregate both/small/large phase summary.json")
    parser.add_argument("output", type=Path, help="New Markdown file")
    parser.add_argument("--recording", type=Path, help="Native recording.json if separate from the decoded tables")
    parser.add_argument("--phase-provenance", type=Path, help="Instrumented provenance.json if separate from its summary")
    parser.add_argument("--python-profile", type=Path, help="Python receipts directory, defaults to a sibling of phases")
    parser.add_argument("--python-pstats", type=Path, help="Optional raw pstats for exact caller attribution")
    parser.add_argument("--unprofiled", type=Path, help="Unprofiled receipts directory, defaults to a sibling of phases")
    parser.add_argument("--native-stage", type=Path, help="Recorder stage receipts, defaults to controller/01-native-record")
    parser.add_argument("--limit", type=int, default=8, help="Maximum rows per global native symbol table")
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be positive")
    record_path = args.recording or args.native_directory / "recording.json"
    provenance_path = args.phase_provenance or args.phase_summary.with_name("provenance.json")
    if args.phase_provenance is not None and not provenance_path.is_file():
        parser.error(f"Missing phase provenance {provenance_path}")
    record, native = read_native(args.native_directory, record_path)
    phases, provenance = read_phases(args.phase_summary, provenance_path, record)
    phases = {scope: phases[scope] for scope in SCOPES}
    lines = ["# Installed jet workflow profile", ""]
    report_native(lines, record, native, args.limit)
    report_phases(lines, phases, provenance)
    evidence = [("Recording and pass receipts", record_path), ("Decoded profile", args.native_directory / "summary.json"),
                ("Owners", args.native_directory / "owners.tsv"), ("Global self", args.native_directory / "self.tsv"),
                ("Global inclusive", args.native_directory / "inclusive.tsv"),
                ("Within-tool self", args.native_directory / "within_owner_self.tsv"),
                ("Within-tool inclusive", args.native_directory / "within_owner_inclusive.tsv"),
                ("Instrumented phases", args.phase_summary)]
    if provenance is not None:
        evidence.append(("Phase provenance", provenance_path))
    final = args.phase_summary.parent.parent
    python_profile = args.python_profile or final / "python-profile"
    if args.python_profile is not None or args.python_pstats is not None or python_profile.is_dir():
        report_python(lines, *read_python(python_profile, phases, provenance, record), args.python_pstats)
        evidence.extend([("Python call and caller summary", python_profile / "summary.json"),
                         ("Python executable and source provenance", python_profile / "provenance.json"),
                         ("Python process audit", python_profile / "visible.json"),
                         ("Python exact histogram proof", python_profile / "histogram-comparison.json")])
    unprofiled = args.unprofiled or final / "native-unprofiled"
    if args.unprofiled is not None or args.native_stage is not None or unprofiled.is_dir():
        stage = args.native_stage or final / "controller/01-native-record"
        report_overhead(lines, read_overhead(unprofiled, stage, record_path, record, phases, provenance),
                        record["repeat"])
        evidence.extend([("Matched unprofiled proof", unprofiled / "diagnostic.json"),
                         ("Matched visible commands", unprofiled / "command.json"),
                         ("Recorder stage start", stage / "started.utc"), ("Recorder stage end", stage / "ended.utc")])
    lines.extend([" · ".join(link(title, path, args.output) for title, path in evidence), ""])
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write("\n".join(lines))


if __name__ == "__main__":
    main()
