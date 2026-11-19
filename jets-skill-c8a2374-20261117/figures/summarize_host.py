"""Match sparse host counter samples to production job legs using their UTC times."""
import argparse
import hashlib
import json
import statistics
from bisect import bisect_left
from datetime import datetime
from pathlib import Path


def identity(path):
    with path.open("rb") as stream:
        return {"file": path.name, "sha256": hashlib.file_digest(stream, "sha256").hexdigest()}


def distribution(values):
    if not values:
        return None
    return {"n": len(values), "minimum": min(values), "median": statistics.median(values),
            "mean": statistics.mean(values), "maximum": max(values)}


def collect(production, logs):
    compact = json.loads(production.read_text(encoding="utf-8"))
    samples = []
    for log in logs:
        with log.open(encoding="utf-8-sig") as stream:
            for line in stream:
                row = json.loads(line)
                measured = datetime.fromisoformat(row["utc"])
                if measured.utcoffset() is None:
                    raise ValueError(f"Missing timezone on host sample in {log}")
                samples.append((round(measured.timestamp() * 1e9), row))
    samples.sort(key=lambda pair: pair[0])
    times = [sample[0] for sample in samples]
    if len(set(times)) != len(times) or not samples:
        raise ValueError("Host samples must be present and uniquely time-stamped")
    counters = ("cpu_percent", "disk_read_bytes_s", "disk_write_bytes_s", "available_memory_MiB",
                "pages_input_s", "wsl_working_bytes")
    legs = []
    groups = {}
    def metrics(rows):
        return {key: distribution([row[key] for row in rows if key in row]) for key in counters}

    for obs in compact["observations"]:
        for name, leg in obs["legs"].items():
            activity = leg.get("guest_activity")
            if activity is None:
                raise ValueError(f"Missing job clock endpoints for {obs['attempt']}")
            start, end = activity["start_unix_ns"], activity["end_unix_ns"]
            left, right = (bisect_left(times, endpoint) for endpoint in (start, end))
            window = [row for _, row in samples[left:right]]
            job = obs["job"]
            group = "/".join([obs["classification"], job["scope"], job["mode"], job["arm"], name])
            groups.setdefault(group, []).extend(window)
            legs.append({"job": job, "classification": obs["classification"], "leg": name,
                         "start_unix_ns": start, "end_unix_ns": end, "host_samples": len(window),
                         "host": metrics(window), "guest_coverage_fraction": activity["coverage_fraction"],
                         "other_guest_cores": activity["external_core_equivalents"],
                         "active_muon_cpu_s": activity["sampled_process_cpu_s"]["muon"]})
    return {
        "method": "Windows counter timestamps inside each half-open worker interval. "
                  "Interval counters describe the whole host, including WSL. Each sample receives equal weight. "
                  "A short leg can contain zero counter samples. Zero samples give no estimate for that leg. "
                  "Guest process attribution comes from the independent interval sampler.",
        "inputs": [identity(path) for path in (production, *logs)],
        "total_host_samples": len(samples), "all_samples": metrics([row for _, row in samples]),
        "sample_gap_s": distribution([(b-a)/1e9 for a, b in zip(times, times[1:])]),
        "pooled_host_samples_by_group": {group: metrics(rows) for group, rows in groups.items()},
        "job_legs": legs,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("production", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("host_logs", type=Path, nargs="+")
    args = parser.parse_args()
    result = collect(args.production, args.host_logs)
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")


if __name__ == "__main__":
    main()
