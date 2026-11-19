# Run the jet calibration on the original PHYSLITE file

Keep `jets_demo.py` and the wheel beside each other. The script declares the local wheel and its Python dependencies. The tested environment was CPython 3.14.10 on x86-64 AlmaLinux 9. A fresh environment needs access to the pinned Python dependencies. The calibration payload, network, CorrectionLib evaluator, and jet provider are included in the wheel.

Run from this directory with a new output filename. In the campaign, CPU 3 was the reserved analysis CPU.

```bash
taskset -c 3 uv run --script jets_demo.py /path/to/original-PHYSLITE.root jets.npz
```

The default reads the whole file once, evaluates both jet collections with their complete configured uncertainty inventories, and writes the histogram arrays. Use `--scope small` or `--scope large` for a single collection, `--mode nominal` for recalibrated nominal jets, or `--mode stored` for the original stored jets. The `-e` option limits events per pass. The `-n` option repeats complete file visits and saves only the last pass. Run `uv run --script jets_demo.py --help` for the full interface.

The validated input is the MC23a full-simulation top-pair sample for DSID 601229, processing tag p7266, ROOT UUID `79ee6652-311f-11f1-aa37-0445010abeef`. It contains 20,000 events with the AnalysisJets and AnalysisLargeRJets collections. The saved arrays include the state names, common transverse-momentum edges in GeV, per-state entry counts, sums of weights and sums of squared weights, including underflow and overflow. [Source and input definition](../reproduce.md) · [Physics comparison](../report.md)
