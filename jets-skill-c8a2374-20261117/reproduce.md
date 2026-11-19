# Reproducing the jet campaign

The authoritative checkout and raw results live in WSL `atlas_al9` at `/home/gwatts/atlas-cp-speed/jets-skill-c8a2374-20261117`. The Windows directory holds the report, plots, editable talk and inspection copies. Use a new checkout and fresh result names to regenerate the campaign. The commands below use Bash inside `atlas_al9`, with CVMFS mounted and guest CPUs 3–5 available. Keep compilation and export outside measured windows. CPU 3 is the single analysis CPU used by the stock and converted acceptance tools. [Frozen sources](evidence/intake/sources.json) · [Workload and acceptance contract](evidence/intake/workload.json)

## Fresh checkout and toolchains

The campaign Git history is local to the authoritative WSL checkout. The checkout below includes the final measurement controller. The Windows source archive contains the tracked source at `01d88b7`, including the implementation that qualified the wheel. Applying the archived timing patch advances those sources to `0b06f13`. The wheel records its packaging commit in `bundle.json`. The provider build records its own revision and actual source hashes in `source-revision.txt` and `source-inputs.sha256`. Restore generated inputs and release dependencies as described below. [Tracked source ZIP](evidence/source/jet-conversion-source.zip) · [Source and submodule identities](evidence/source/jet-conversion-source.json) · [Timing patch](evidence/source/production-timing.patch) · [Patch identity](evidence/source/production-timing.json)

```bash
archive=/home/gwatts/atlas-cp-speed/jets-skill-c8a2374-20261117
new_checkout=/home/gwatts/atlas-cp-speed/jets-reproduction
campaign_revision=0b06f13f140db0c34c73bfe0676cd429849ff72c
git clone --no-hardlinks "$archive" "$new_checkout"
cd "$new_checkout"
git checkout --detach "$campaign_revision"
git submodule update --init --recursive --jobs 1
test "$(git -C source/correctionlib rev-parse HEAD)" = 3dcfa20ec01fb40c4d5fec58383785519dec1c00
git submodule status --recursive
mkdir -p results/{reference,export,build,framework,packaging,validation,diagnostics,benchmarks}
```

Use the recursive submodule pins for the evaluator and its vendored dependencies, including RapidJSON. The local source must contain the pinned refs and version tags used by the evaluator build. AnalysisBase `25.2.117` and AnalysisBaseExternals for `x86_64-el9-gcc15-opt` provide the framework headers, dictionaries, ROOT and calibration resolver. The portable build and evaluator use the release's GCC 15.2.0. Stock PyROOT and the standalone **CPython 3.14.10** environments are separate. [Recursive evaluator submodule pins](evidence/intake/evaluator-submodules.txt)

```bash
uv=/cvmfs/sft.cern.ch/lcg/releases/uv/0.11.21-24fd6/x86_64-el9-gcc15-opt/bin/uv
python=/home/gwatts/.local/share/uv/python/cpython-3.14.10-linux-x86_64-gnu/bin/python3.14
# Provision the recorded interpreter under the account used by the build scripts.
if [[ ! -x "$python" ]]; then "$uv" --native-tls python install 3.14.10; fi
"$python" -VV
"$python" -m venv .reference-venv
"$uv" pip install --native-tls --python .reference-venv/bin/python -r tools/reference/requirements.lock
```

`tools/build-core.sh` and `tools/build_jet_shipment.sh` expect the exact interpreter path above. Provide that interpreter or adapt the path in a separately recorded local change on another account. The evaluator build uses CMake 3.20.2 and Ninja. The lwtnn archive uses Unix Makefiles. Native assembly and its audit also require the standard linker, `readelf` and `ldd`. Use a fresh shell without inherited release Python or loader paths for standalone Python and wheel commands.

## Original file and numerical authority

The setup script selects the installed release, thread caps and original test file. The 20,000-entry `CollectionTree` has TFile UUID `79ee6652-311f-11f1-aa37-0445010abeef` and input SHA-256 `017e408002b0153df1de695d8c2ace325e0731b658cbd5ca695a349eb0a059c0`. The scope configurations in `config/` select the uncertainty models. A separate observer records each original object before final event or object selection.

```bash
(
  source tools/reference/setup.sh
  printf '%s  %s\n' 017e408002b0153df1de695d8c2ace325e0731b658cbd5ca695a349eb0a059c0 \
    "$JETS_REFERENCE_INPUT" | sha256sum -c -
  bash tools/reference/build-observer.sh
)
# This exact directory name is an input to the uncertainty exporter.
taskset -c 3 bash tools/reference/run-observer.sh results/reference/observer-smoke-003 8
taskset -c 3 bash tools/reference/run-observer.sh results/reference/full-clean-001 20000

for scope in small large combined; do
  taskset -c 3 env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
    .reference-venv/bin/python tools/reference/benchmark.py run \
    "results/reference/full-file-pilot-$scope-002" --events 20000 --pilot --scope "$scope"
done
taskset -c 3 env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  .reference-venv/bin/python tools/reference/benchmark.py run \
  results/reference/benchmark-pilot-combined-002 --events 32 --pilot --scope combined
```

The small initialization run generates `initialized-tools.tsv`, including recommended and affecting states for both jet sizes and their pseudo-data tools. To replay an existing export, restore the exact file from the authoritative `results/reference/observer-smoke-003/` archive at that path. The full observer writes `reference.root` and `hist-reference.root`. The three uninstrumented stock pilots separately write the independent `01-full/histograms.npz` endpoints used for parity. Their `provenance.json` and per-leg receipts identify the input, release and scope. The 32-event pilot supplies the stock histogram for the installed physical-order check. [Original process and file verification](evidence/reference/full-clean-001/verification.json)

## Resolve, export, pack and project the payloads

The release export needs the release Python, PyROOT, `PathResolver`, `CALIBPATH` and the initialized-tools file. It resolves each TEnv and ROOT input at export time, retains the referenced objects and writes their resolved paths, byte counts and hashes into `provenance.json`. The optional early resolver probe in the archived `results/discovery/small-source/` is inspection evidence. The bundle exporter resolves its own inputs.

```bash
mkdir results/export/reproduction-faithful
(
  source tools/reference/setup.sh
  taskset -c 4 python - <<'PY'
from pathlib import Path
from exporters.bundle import export_bundle

export_bundle(Path('results/export/reproduction-faithful/payload'))
PY
)

py=.reference-venv/bin/python
faithful=results/export/reproduction-faithful/payload
portable=results/export/reproduction-portable
packed=results/export/reproduction-packed
partition=results/export/reproduction-partition
mkdir "$portable"
taskset -c 4 "$py" -m exporters.portable_uncertainty \
  "$faithful/jets.json" "$portable/jets.json" "$portable/plan.json"
cp "$faithful/provenance.json" "$portable/provenance.json"
taskset -c 4 "$py" -m exporters.pack_eta_jes "$portable/jets.json" "$packed"
taskset -c 4 "$py" -m exporters.partition_payload "$packed/jets.json" "$partition"
taskset -c 4 "$py" exporters/prepare_scope_index.py \
  "$packed/jets.json" "$partition" "$partition/payload-index.json"
```

The release export contains 15 corrections. Portable plan generation adds the two resolved uncertainty evaluation plans to those corrections and preserves their original data-source receipt. The packing receipt identifies the inherited provenance and separately records the packed payload digest. Only the EtaJES TH1F response cells are packed as little-endian IEEE binary32. The packer checks exact recovery of the stored bits. Partitioning preserves each retained correction's raw bytes. `prepare_scope_index.py` reconstructs the two scope documents from the canonical packed file and verifies both against the prebuilt files. The shipped wheel needs the canonical file and index. Scoped framework and engineering comparisons can load `scopes/small/jets.json` or `scopes/large/jets.json` directly. [Release calibration bytes](evidence/diagnostics/source-bytes-001.json) · [Correction inventory](evidence/diagnostics/manifest.json)

The corresponding archived outputs are `results/export/complete-005/payload`, `results/export/portable-001`, `results/export/eta-jes-packed-001` and `results/export/eta-jes-partition-001`. Their faithful, portable and packed `jets.json` SHA-256 values begin `795df3b7`, `b723ef7e` and `1aed4df0`. Restore the entire export chain, including each sibling `provenance.json`, when verifying an archived wheel. Relative symlinks in the partition need their packed export target.

## Build the evaluator and native libraries

The precision-core script clones the pinned evaluator, applies the full-precision JSON parsing patch and verifies the resulting Git tree `881728c52c0428f1772776ec5283fc4fa806a511`. Then it builds and installs one `cp314-cp314-linux_x86_64` evaluator wheel in the named result directory. The faithful provider and framework overlay use that SDK together with the installed release libraries. [Parser comparison](evidence/diagnostics/full-precision-parser.json) · [ROOT fixture](evidence/diagnostics/portable-vector-stream.txt)

```bash
taskset -c 4 bash tools/build-precision-core.sh reproduce-core
taskset -c 4 bash tools/build-provider.sh reproduce-faithful reproduce-core
sdk="$PWD/results/build/reproduce-core/venv/lib/python3.14/site-packages/correctionlib"
taskset -c 4 bash tools/build-framework.sh reproduce-framework "$sdk" full
```

The portable provider uses the position-independent `lwtnn-stat` archive built from the release's lwtnn 2.14.1 source, upstream commit `102b58d95ca5cb926a87fae0ef0b88583ec4abad`. `portable/lwtnn-dependency.json` records the source release tarball, license, and CMake options. Use system GCC **11.3.1** for this static archive and the pinned release headers for Eigen 3.4.1 and Boost 1.91.0. Keep the GCC 15 setup inside the build scripts and any release setup inside the subshells shown above.

```bash
lwtnn=reproduce-lwtnn
dest="$PWD/results/build/$lwtnn"
externals=/cvmfs/atlas.cern.ch/repo/sw/software/25.2/AnalysisBaseExternals/25.2.117/InstallArea/x86_64-el9-gcc15-opt
mkdir "$dest"
if [[ -f "$archive/results/build/portable-lwtnn-001/v2.14.1.tar.gz" ]]; then
  cp "$archive/results/build/portable-lwtnn-001/v2.14.1.tar.gz" "$dest/"
else
  curl --fail --location --output "$dest/v2.14.1.tar.gz" \
    https://cern.ch/atlas-software-dist-eos/externals/lwtnn/v2.14.1.tar.gz
fi
(
  cd "$dest"
  printf '%s  %s\n' e0ec31f7129014324b91d2b7a6380bf1e9c571fa4b39577112192255d4fa83a9 \
    v2.14.1.tar.gz | sha256sum -c -
  tar -xzf v2.14.1.tar.gz
)
taskset -c 4 /usr/bin/cmake -S "$dest/lwtnn-2.14.1" -B "$dest/build" -G 'Unix Makefiles' \
  -DCMAKE_C_COMPILER=/usr/bin/cc -DCMAKE_CXX_COMPILER=/usr/bin/c++ \
  -DCMAKE_PREFIX_PATH="$externals" -DEIGEN3_INCLUDE_DIR="$externals/include/eigen3" \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_POSITION_INDEPENDENT_CODE=ON '-DCMAKE_CXX_FLAGS=-ffp-contract=off'
taskset -c 4 /usr/bin/cmake --build "$dest/build" --target lwtnn-stat --parallel 1
sha256sum "$dest/build/lib/liblwtnn-stat.a"
taskset -c 4 bash tools/build-portable.sh reproduce-portable reproduce-core "$lwtnn"
taskset -c 5 bash tools/build-portable.sh reproduce-selected reproduce-core "$lwtnn" \
  rng-cache-large fast-variable-flow unsigned-sign-pairs rng-prefix \
  large-jmr-match-cache variable-axis-index
```

The first portable command reproduces the default build. The second uses the six native options in the observed 006 provider receipt. It enables the 262,144-slot original-stream RNG cache, variable-flow and axis lookup changes, unsigned sign-pair evaluation, original-stream MT prefix and large-R truth-match reuse. Compile-time support for sign-pair evaluation is separate from the workflow setting that selects the states that use it. To replay the archived static dependency, restore `results/build/portable-lwtnn-001/build/lib/liblwtnn-stat.a`, verify SHA-256 `8735c1434418827e815304ef49fe6a639f0eba0a42b3c5270a19c81cd9a282ad`, and use `portable-lwtnn-001` as the third build argument. The archive's initial wrapper returned nonzero after a successful static build because its link probe omitted the `lib/` path. `link-localized-001/build.sha256` records the corrected link probe and the archive used by the provider.

## Assemble and install the standalone wheel

The shipment build requires the evaluator wheel, the selected portable `libjets.so`, the packed canonical `jets.json` with its sibling provenance, the audited partition, the GCC 15.2.0 runtime libraries and **patchelf 0.19.3.0**. Its wrapper reads packaging tools and notices from `results/packaging/build-tools-001`. The seven raw AnalysisBase, GCC, ROOT adaptation and lwtnn notices are retained there in WSL, outside Git. The wheel also includes the evaluator's vendored dependency licenses from the pinned submodules. Restore the archived notice files and hash manifest or recover the same bytes from `*.dist-info/licenses/atlas-jets/` inside a verified shipped wheel.

```bash
build_tools=results/packaging/build-tools-001
mkdir "$build_tools"
cp -a "$archive/$build_tools/licenses" "$build_tools/"
cp "$archive/$build_tools/LICENSES-complete.sha256" "$build_tools/"
sha256sum -c "$build_tools/LICENSES-complete.sha256"
"$uv" venv --python "$python" "$build_tools/venv"
"$uv" pip install --native-tls --python "$build_tools/venv/bin/python" \
  annotated-doc==0.0.6 annotated-types==0.8.0 markdown-it-py==4.3.0 mdurl==0.1.2 \
  patchelf==0.19.3.0 pydantic==2.14.3 pydantic-core==2.50.4 pygments==2.21.0 \
  rich==15.0.0 shellingham==1.5.4 typer==0.29.1 typing-extensions==4.16.0 typing-inspection==0.4.5

# Fresh serial with the observed 006 native and visible-workflow options.
bash tools/build_jet_shipment.sh 101 reproduce-core \
  results/build/reproduce-selected/libjets.so "$packed/jets.json" "$partition" both \
  --sign-default-scope small --sign-default-scope both --large-chunk-events 4000
(cd results/packaging/bundle-101 && sha256sum -c SHA256SUMS)
```

The wrapper builds and relocates the wheel on CPU 5, audits its ELF dependency closure, generates the PEP 723 entry point and makes fresh pip and uv installations. The `both` compact setting enables compact defaults separately for `--scope small` and `--scope large`. The combined workflow uses the canonical packed document. The wheel receipt records the selected scope options and hashes for the script, evaluator, libraries, payload, projector and index. The build and install need the archived packages or access to the package index. `tools/build-core.sh` uses live resolution for Python build prerequisites and creates a local patch commit. A clean build can reproduce the source tree and scientific endpoint while producing a different wheel version or hash. Use the accepted core/provider and the archived bundle and its `SHA256SUMS` for byte-identity replay.

## Recheck the validated faithful framework

When rerunning these checks against the existing accepted binaries, use their pinned SDK. An observer check writes a large ROOT file covering all states before making the independent comparison. The stock histogram is the independently saved combined full-systematics histogram.

```bash
sdk="$archive/results/build/core-precision-002/venv/lib/python3.14/site-packages/correctionlib"
taskset -c 3 bash "$archive/tools/verify-framework.sh" \
  "$archive/results/build/full-001/overlay" \
  "$archive/results/build/complete-005/libjets.so" \
  "$archive/results/export/complete-005/payload/jets.json" "$sdk" \
  "$PWD/results/framework/reproduction-full" \
  "$archive/results/reference/full-clean-001/reference.root" \
  "$archive/results/reference/full-file-pilot-combined-002/01-full/histograms.npz"
```

For a fresh rebuild, run the copy of `tools/verify-framework.sh` in the new checkout with the new SDK, `results/build/reproduce-framework/overlay`, `results/build/reproduce-faithful/libjets.so` and `results/export/reproduction-faithful/payload/jets.json`. Point the final two arguments at this checkout's regenerated stock outputs. Use a new acceptance output directory.

## Run the independently validated portable checkpoint

The archived portable checkpoint's visible PEP 723 example and local wheel are together under `results/packaging/bundle-003`. Its pinned dependencies include CPython 3.14, uproot, Awkward, NumPy, hist, Typer and the local CorrectionLib. `-n` repeats complete input-file visits. `-e` restricts the number of events in each visit. The command explicitly selects both collections and all configured states. The original file is read once per pass and only the last pass's histograms are written.

```bash
uv=/cvmfs/sft.cern.ch/lcg/releases/uv/0.11.21-24fd6/x86_64-el9-gcc15-opt/bin/uv
input=$(source tools/reference/setup.sh >/dev/null && realpath "$JETS_REFERENCE_INPUT")
bundle="$archive/results/packaging/bundle-003"
output="$PWD/results/validation/reproduction-portable.npz"
(cd "$bundle" && env -u PYTHONPATH -u PYTHONHOME -u LD_LIBRARY_PATH -u LD_PRELOAD \
  taskset -c 3 "$uv" run --no-project --no-config --native-tls --no-python-downloads \
  --python "$python" --script jets_demo.py "$input" "$output" --scope both --mode full)
```

The scientific comparison uses the installed wheel's native library and payload, the same original PHYSLITE file and the stock observer. The independent native energy helper computes the derived small-radius energy with the validated four-vector operation. The remaining persisted names are reconciled separately by `tools/compare_columnar_aliases.py`. [Direct full-file result](evidence/portable/full-comparison.json) · [Alias and energy agreement](evidence/portable/observer-aliases.json) · [PEP 723 and pip checks](evidence/portable/final-visible-smoke.json)

For a new checkout, `tools/validate_direct_release.sh` expects the native energy helper at `results/build/columnar-alias-energy-portable-001/libcolumnar-alias-energy.so`. Restore that file from the WSL archive or rebuild it from `tools/columnar_alias_energy.cxx` with the portable four-vector header and the recorded GCC 11.3.1 compiler.

```bash
energy_build=results/build/columnar-alias-energy-portable-001
mkdir "$energy_build"
taskset -c 5 /usr/bin/g++ -std=c++20 -DJETS_PORTABLE -O2 -ffp-contract=off -fPIC -shared \
  tools/columnar_alias_energy.cxx -o "$energy_build/libcolumnar-alias-energy.so"
```

## Timing boundaries

`tools/benchmark_campaign.py` runs or resumes the A/B/C grid. Its journal stores every leg, exact launch arguments, CPU and wall time, peak resident memory, affinity, sampled processes, native libraries and saved histogram guard. `tools/compact_campaign.py` verifies the saved digests and collects each observation into a shareable JSON file. [Warm-up command identities and raw observations](evidence/timing/faithful/round-zero-only.json)

## Selected 006 shipment

The observed shipment is `results/packaging/bundle-006` with pristine installations in `results/packaging/pristine-006`. The bundle source revision is `04c9e4abc60f26dcb16d88f68dfad7f9933436e6`. The native provider in `results/build/final-prefix-truth-index-001` records source revision `02c25d9dc4625912c56a9990899064b9d8cf13c8` and its actual source-file hashes. Use the archived binaries and original `SHA256SUMS` for an exact replay. A fresh rebuild uses the preceding sections and a new serial.

| Observed artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `correctionlib-0.1.dev230+g0c498f4cb.atlasjets6-cp314-cp314-linux_x86_64.whl` | 36,078,219 | `45752f8c5c125db01f4def932ef97cb4d732ce90f34d120446e69025a895cf78` |
| `jets_demo.py` | 31,776 | `da24441a0302574de38ed3e82d5f5ee719ed5856ef63a30ecbea76347e504a05` |
| `bundle.json` | 4,106 | `97e609ff294d738c16e6999eeb4a58b2d9a482e764b47f6d2fb7d864c3eff473` |
| Original selected `libjets.so` | 16,970,800 | `d4c17d1bf9156a4684077c5327539e2aaa7caab321ea57cdd4f37197c3c3379a` |
| Canonical packed `jets.json` | 75,847,478 | `1aed4df05b75b208ec23dc61c3de9d04e76b5f90cc561407d2e20ed89a0a4cc7` |
| `payload-index.json` | 687 | `570576400e928ebfe2ee53dcd7594dd9d9689bb85814a7239e8bf90f2beecbda` |

The 006 CLI defaults to both collections and all configured systematics, one pass over the original input. It uses 1,000 events per chunk for small-R and combined, and 4,000 for large-R only. A single collection loads the indexed projection in a calibrated mode. Combined loads the canonical packed document. Small-R full and combined full enable validated nominal NNJvt reuse and unsigned sign-pair reuse. Stored mode loads only persisted values. Framework jobs use the installed-release overlay, selected native provider and equivalent prebuilt scoped payloads. The standalone wheel records the separate identity of its relocated provider.

```bash
cd "$archive"
bundle="$PWD/results/packaging/bundle-006"
installation="$PWD/results/packaging/pristine-006"
input=$(.reference-venv/bin/python -c 'import json; print(json.load(open("config/jets-input.json"))["path"])')
input=$(realpath "$input")
output="$PWD/results/validation/reproduction-selected-both.npz"
(cd "$bundle" && sha256sum -c SHA256SUMS)

# Replay the installed command shape with the 006 script's actual defaults.
env -u PYTHONPATH -u PYTHONHOME -u LD_LIBRARY_PATH -u LD_PRELOAD \
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 taskset -c 3 \
  "$installation/pip/env/bin/python" "$bundle/jets_demo.py" "$input" "$output" --events 20000

# A PEP 723 entry point using the adjacent verified wheel and a fresh output.
(cd "$bundle" && env -u PYTHONPATH -u PYTHONHOME -u LD_LIBRARY_PATH -u LD_PRELOAD \
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 taskset -c 3 \
  "$uv" run --no-project --no-config --native-tls --no-python-downloads \
  --python "$python" --script jets_demo.py "$input" "${output%.npz}-uv.npz")
```

Use `--scope small` or `--scope large` for a single collection. Use `--mode stored` or `--mode nominal` for the control workload. The formal C nominal and full controls also set `--matched-read` to equalize the physical branch requests and truth preparation. The stock production configs use `combined` where the standalone CLI uses `both`.

## Selected shipment qualification

The pinned specification is `contracts/final-shipment.json`. Its controller receipt is `results/diagnostics/qualify-selected-001/steps`, and it writes `results/validation/shipment-final-001`. The exact historical command shape is `bash tools/verify_shipment_workflows.sh contracts/final-shipment.json results/diagnostics/qualify-selected-001/steps`. The controller requires fresh destinations. To replay with the same artifacts, make a new specification that changes only the output path.

```bash
cd "$archive"
mkdir -p results/diagnostics
spec=contracts/final-shipment.json
replay_spec=results/diagnostics/qualification-replay.json
replay_output=results/validation/shipment-replay-001
.reference-venv/bin/python - "$spec" "$replay_spec" "$replay_output" <<'PY'
import json
from pathlib import Path
import sys
original, replay, output = sys.argv[1:]
config = json.loads(Path(original).read_text())
config["output"] = output
with Path(replay).open("x") as stream:
    json.dump(config, stream, indent=2)
    stream.write("\n")
PY
bash tools/verify_shipment_workflows.sh "$replay_spec" results/diagnostics/qualify-replay-001
```

The controller runs calibration serially on CPU 3 with one processing thread. It decodes native stacks on CPU 5. Native sampling records ten complete passes and requires at least 60 seconds of worker CPU over passes 2–10. The matched unprofiled diagnostic runs the same ten-pass command with a separate output. The phase study records setup, input reads, per-tool calls, histogram filling, output and the startup/teardown remainder. The single combined `cProfile` pass has the delivered defaults and writes raw pstats to WSL plus summaries with caller edges. These diagnostics verify saved histograms against independent stock output. The controller then checks chunk and file order, reconciles object values and framework decorations, and verifies each scope through the installed pip and uv entry points. Each stage has its own command, exit, start/end and log receipt.

## Formal campaign, progression and bounded recheck

Run formal timing only after qualification and with the analysis CPU reserved. Use the specification whose `output` contains the corresponding validated receipts. The production command resumes its own journal and accepts `--jobs N` to bound the next batch of jobs. It schedules 108 primary jobs across three scopes, three modes, three paths and four rounds, plus four combined/full stock anchors. The opening round is excluded. The three retained rounds alternate the path order. Retained reports require a coefficient of variation at most 5% and maximum deviation from the median at most 10%, with stock-anchor drift checked separately. Keep the original file, event order, sealed projection and selection behavior, and one calibration thread for each paired control.

```bash
cd "$archive"
spec=contracts/final-shipment.json
production=results/validation/shipment-final-001/production-replay-001
monitor=results/diagnostics/production-replay-monitor-001
bash tools/run_production_with_monitor.sh "$spec" "$monitor" --production-output "$production"
.reference-venv/bin/python tools/compact_campaign.py "$production" \
  results/benchmarks/selected-production-compact.json --guest-log "$monitor/guest.jsonl"
```

The production journal is `results/validation/shipment-final-001/production-002`. Three non-overlapping sessions, `results/diagnostics/production-monitor-002`, `-003` and `-004`, cover all 112 accepted jobs. To reproduce the compact file from the journal, pass one `--guest-log` option for each of those three `guest.jsonl` files. The Windows sampler writes a separate completion receipt for each session. A prior journal used monitor 001 and timed two warm-ups before a 0.493 s control exposed insufficient library-map sampling. Its observations stay with that journal. [Windows launch and host sampling](evidence/timing/run-monitored.ps1) · [Initial diagnostic](evidence/timing/production/monitor-001/stored-control-rejection.json) · [112-job compact archive](evidence/timing/production/compact.json)

For columnar C, the numerator is A's stock framework time plus the separate histogram time. The denominator is the real installed script from process start through saved histogram and exit, including payload materialization where selected. The axis of comparison for the 1.20× B budget is B framework time divided by A framework time. The histogram guard still applies to B. Production controls and diagnostics remain distinct.

The standalone progression is a separate full-systematics comparison. It rotates scope and arm across four rounds, excludes round one, and times each fresh CLI through the exact saved histogram. The faithful command selects the scope and full workload explicitly and uses its prebuilt scoped payload. Bundles 005 and 006 run their sealed full-workflow defaults for each requested scope. The receipt records an explicit omission if the archived faithful arm cannot be recovered. It also records identical branch-set digests by scope.

```bash
taskset -c 3 env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  .reference-venv/bin/python packaging/compare_shipment_progression.py \
  results/packaging/pristine-006 results/packaging/bundle-006 \
  results/benchmarks/selected-progression-001
```

A paired recheck requires a completed original production journal and an unqualified ratio due to spread, drift, or retained pairs straddling the applicable threshold. It runs one scope and mode for one A/B or A/C pair. It uses ten jobs, with stock brackets before and after four paired rounds. The first pair is excluded. Stock, exact histogram, artifact, projection, physical read and execution guards stay pinned to the original cohort. Four decisions in the original grid met the recheck rule: A/B small-R nominal, A/C large-R full, A/C combined full and A/B combined full. The A/B example below reproduces the first decision. Set `production` to the completed original journal or a completed replay for which this pair also qualifies. Keep the receipts in their own fresh directory and report both observations.

```bash
taskset -c 3 env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  .reference-venv/bin/python tools/qualify_shipment.py "$spec" time \
  --recheck-of "$production" --recheck-scope small --recheck-mode nominal \
  --recheck-pair AB --recheck-output results/benchmarks/selected-small-nominal-ab-recheck-001
```

The matched progression used `results/diagnostics/shipment-progression-001` and guest monitor `progression-monitor-003`. Its faithful source was recovered from `7b296d18d48f2c4a4105ba387141c6edccd86bcf`. The complete original, packed and selected commands are in the archived provenance. The four bounded journals are under `results/validation/shipment-final-001/`, beside `production-002`. Their names encode the pair, collection, workload and serial. [Progression commands and identities](evidence/timing/progression/provenance.json) · [Measurement definitions and bounded decisions](timing-results.md)

## Recreate the report figures and tables

The scientific figures read the independently saved stock and installed results in the Windows report. The complete native recording and raw Python pstats stay in WSL. The commands below regenerate plots from the archived arrays and classification tables. Each plotting script declares its dependencies. The Markdown generators create new files. Pass any completed bounded recheck to the timing generator using one `--recheck-summary` option per receipt.

```bash
cd "$archive"
report="/mnt/c/Users/gwatts/OneDrive/Documents/ATLAS/Computing/AMG/CorrectionLib/jets-skill-c8a2374-20261117"
evidence="$report/evidence/final"
uv=/cvmfs/sft.cern.ch/lcg/releases/uv/0.11.21-24fd6/x86_64-el9-gcc15-opt/bin/uv
python=/home/gwatts/.local/share/uv/python/cpython-3.14.10-linux-x86_64-gnu/bin/python3.14
for plot in plot_endpoints.py plot_pt.py plot_profile.py plot_timings.py; do
  taskset -c 5 env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 "$uv" run \
    --index-url https://pypi.org/simple --python "$python" --script "$report/figures/$plot"
done
"$python" "$report/figures/summarize_profile.py" "$evidence/native" \
  "$evidence/phases/summary.json" "$report/profile-replay.md" \
  --python-pstats results/validation/shipment-final-001/python-profile/profile.pstats
checks=()
for pair in AB-small-nominal AC-large-full AC-combined-full AB-combined-full; do
  checks+=(--recheck-summary "$report/evidence/timing/recheck-${pair}-001/summary.json")
done
"$python" "$report/figures/summarize_timings.py" --resources "${checks[@]}" \
  --production "$report/evidence/timing/production/compact.json" --output "$report/timing-replay.md"
"$python" "$report/talk/build-performance-content.py" "${checks[@]}" \
  --production "$report/evidence/timing/production/compact.json" \
  --progression "$report/evidence/timing/progression/summary.json" \
  --output "$report/talk/performance-replay.json" --reader-output "$report/talk/reader-replay.json"
```

The compact timing archive records which accepted job attempt supplied each measurement. Its hashes identify the controller's raw histogram and resource receipts. Windows host counters have their own UTC timestamps. The host summary matches each observation to its measured job leg and retains a missing estimate if a short leg contains no host sample. [Guest timing reduction and source revision](evidence/source/jet-conversion-source.json) · [Host correlation code](figures/summarize_host.py)

On Windows, run the following from the report directory with desktop PowerPoint installed. The deck builder takes a fresh output name, writes the editable slides and speaker notes, and exports every slide at 1440 × 810 for visual inspection. The original final deck used the identical source with `performance-content.json`.

```powershell
& ./talk/build-deck.ps1 -OutputName jets-calibration-replay.pptx -TimingFile (Resolve-Path ./talk/performance-replay.json)
```
