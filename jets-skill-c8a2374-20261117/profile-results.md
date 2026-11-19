# Installed jet workflow profile

## Native processing profile

The Combined run made 10 complete visits to the original 20,000-event PHYSLITE file, containing 196,606 small-R and 22,177 large-R jets. The final saved histogram matched stock in all 10 fields. The worker and collector ran on CPU 3 with one calibration thread.

The sampled interval runs from observed completion of pass 1 through pass 10. It covers 105.94 s of wall time and a conservative worker CPU floor of 104.08 s against the required 60 s. Across those 9 visits this is 11.772 s wall and at least 11.564 s worker CPU per file. The CPU floor uses the tick-adjusted interior snapshots recorded by the controller.

Perf used `cpu-clock:u` with DWARF stacks and a configured 10 ms period. The denominator is 10,536 accepted user-space sample periods summing to 105.360 s, or 11.707 sampled CPU s per file. The decoder used recorded CPU and worker PID and sample weights recorded per sample. The repeated processing window and the fresh-start phase diagnostic answer different measurements.

| Stack coverage | Observed |
| --- | --- |
| Samples outside the processing window | 1,314 |
| Accepted samples with a recorded CPU | 10,536 / 10,536 |
| Samples from an unexpected worker or CPU | 0 |
| Samples with an unresolved leaf symbol | 2,042 / 10,536 (19.38%) |
| Samples with no resolved frame | 1,765 / 10,536 |
| Samples with an inline leaf and no resolved module | 0 |
| Inline decoder defects | 0 |
| Physical decoder defects | 0 |

### Disjoint tool and runtime ownership

Each sample is assigned to the nearest identifiable provider stage using physical frames and then inline symbols. A stage can own a sample whose leaf function is unresolved. The shared uncertainty owner pools both radii in the combined recording. The instrumented table below gives the measured calls by radius, including calls whose native stacks did not receive a named sample owner.

| Owner scope | Sampled CPU s/file | Share |
| --- | --- | --- |
| infrastructure/unknown | 5.031 | 42.98% |
| shared | 3.853 | 32.92% |
| small-R | 2.549 | 21.77% |
| large-R | 0.273 | 2.33% |

| Executing tool or runtime group | Scope | Samples | Sampled CPU s/file | Share |
| --- | --- | --- | --- | --- |
| JES/JER/JMS uncertainties | shared | 3,322 | 3.691 | 31.53% |
| NNJVT update | small-R | 1,610 | 1.789 | 15.28% |
| Unresolved stack owner | infrastructure/unknown | 1,429 | 1.588 | 13.56% |
| CorrectionLib without a named tool | infrastructure/unknown | 1,347 | 1.497 | 12.78% |
| Array operations | infrastructure/unknown | 1,336 | 1.484 | 12.68% |
| NNJVT scale factor | small-R | 399 | 0.443 | 3.79% |
| Histogram fill | infrastructure/unknown | 208 | 0.231 | 1.97% |
| NNJVT selection | small-R | 159 | 0.177 | 1.51% |
| Decompression | infrastructure/unknown | 144 | 0.160 | 1.37% |
| Large-R selections | large-R | 127 | 0.141 | 1.21% |
| Forward-folded JMR | large-R | 114 | 0.127 | 1.08% |
| Global sequential calibration | small-R | 81 | 0.090 | 0.77% |
| Pileup truth labelling | shared | 79 | 0.088 | 0.75% |
| EtaJES | shared | 65 | 0.072 | 0.62% |
| Python or other native work | infrastructure/unknown | 62 | 0.069 | 0.59% |
| Event scale factor | small-R | 40 | 0.044 | 0.38% |
| Pileup calibration | small-R | 5 | 0.006 | 0.05% |
| Nominal JMS | large-R | 5 | 0.006 | 0.05% |
| Event inputs | shared | 2 | 0.002 | 0.02% |
| Jet provider without a named tool | infrastructure/unknown | 2 | 0.002 | 0.02% |

### Hottest native routines

Self time assigns each accepted sample to its logical leaf. Inclusive time counts a routine once per stack, including samples spent in callees. Inclusive rows overlap. The tables are sorted independently by measured weight. Full demangled symbols are available in the linked TSVs.

| Routine by self time | Module | Sampled CPU s/file | Window share |
| --- | --- | --- | --- |
| `[unknown]` | `[unknown]` | 1.588 | 13.56% |
| `correction::PluginNode::evaluate_batch_array(std::vector<correction::BatchInput, std::allocator<…> > const&, un…` | `libcorrectionlib.so` | 0.638 | 5.45% |
| `jets::JetUncertaintyModel::Impl::evaluate(jets::JetUncertaintyInput const&, jets::(anonymous namespace)::State …` | `libjets.so` | 0.460 | 3.93% |
| `correction::BatchInput::at[abi:cxx11](unsigned long) const` | `libcorrectionlib.so` | 0.441 | 3.77% |
| `__gnu_cxx::__normal_iterator<double const*, std::vector<double, std::allocator<…> > > std::__lower_bound<__gnu_…` | `libjets.so` | 0.319 | 2.72% |
| `__memcmp_avx2_movbe` | `libc.so.6` | 0.302 | 2.58% |
| `_int_malloc` | `libc.so.6` | 0.257 | 2.19% |
| `_int_free` | `libc.so.6` | 0.234 | 2.00% |

| Routine by inclusive time | Module | Sampled CPU s/file | Window share |
| --- | --- | --- | --- |
| `[unknown]` | `_core.cpython-314-x86_64-linux-gnu.so` | 8.172 | 69.81% |
| `correction::Correction::evaluate_batch_array(std::vector<correction::BatchInput, std::allocator<…> > const&, un…` | `libcorrectionlib.so` | 8.056 | 68.81% |
| `correction::PluginNode::evaluate_batch_array(std::vector<correction::BatchInput, std::allocator<…> > const&, un…` | `libcorrectionlib.so` | 8.051 | 68.77% |
| `(anonymous namespace)::JetUncertaintyNode::evaluate_array(std::vector<std::variant<long, double, std::__cxx11::…` | `libjets.so` | 3.692 | 31.54% |
| `jets::JetUncertaintyModel::evaluate(jets::JetUncertaintyInput const&, std::__cxx11::basic_string<char, std::cha…` | `libjets.so` | 3.203 | 27.36% |
| `jets::JetUncertaintyModel::Impl::evaluate(jets::JetUncertaintyInput const&, jets::(anonymous namespace)::State …` | `libjets.so` | 2.872 | 24.53% |
| `evaluate_array` | `libjets.so` | 1.862 | 15.91% |
| `(anonymous namespace)::NnJvtUpdate::evaluate_array(std::vector<std::variant<long, double, std::__cxx11::basic_s…` | `libjets.so` | 1.793 | 15.32% |

### Routines within each named tool

For each sampled tool the table shows the two heaviest self and inclusive routines. The final two columns use the tool’s owned samples and the whole processing window respectively.

| Tool | Scope | Basis | Routine | Module | Tool share | Window share |
| --- | --- | --- | --- | --- | --- | --- |
| JES/JER/JMS uncertainties | shared | self | `jets::JetUncertaintyModel::Impl::evaluate(jets::JetUncertaintyInput const&, jets::(anonymous namespace)::State …` | `libjets.so` | 12.34% | 3.89% |
| JES/JER/JMS uncertainties | shared | self | `__gnu_cxx::__normal_iterator<double const*, std::vector<double, std::allocator<…> > > std::__lower_bound<__gnu_…` | `libjets.so` | 8.04% | 2.53% |
| JES/JER/JMS uncertainties | shared | inclusive | `correction::Correction::evaluate_batch_array(std::vector<correction::BatchInput, std::allocator<…> > const&, un…` | `libcorrectionlib.so` | 100.00% | 31.53% |
| JES/JER/JMS uncertainties | shared | inclusive | `[unknown]` | `_core.cpython-314-x86_64-linux-gnu.so` | 100.00% | 31.53% |
| NNJVT update | small-R | self | `_int_free` | `libc.so.6` | 10.06% | 1.54% |
| NNJVT update | small-R | self | `malloc` | `libc.so.6` | 9.75% | 1.49% |
| NNJVT update | small-R | inclusive | `correction::Correction::evaluate_batch_array(std::vector<correction::BatchInput, std::allocator<…> > const&, un…` | `libcorrectionlib.so` | 100.00% | 15.28% |
| NNJVT update | small-R | inclusive | `[unknown]` | `_core.cpython-314-x86_64-linux-gnu.so` | 100.00% | 15.28% |
| NNJVT scale factor | small-R | self | `[unknown]` | `libcorrectionlib.so` | 32.08% | 1.21% |
| NNJVT scale factor | small-R | self | `(anonymous namespace)::NnJvtSf::evaluate_array(std::vector<std::variant<long, double, std::__cxx11::basic_strin…` | `libjets.so` | 12.78% | 0.48% |
| NNJVT scale factor | small-R | inclusive | `correction::Correction::evaluate_batch_array(std::vector<correction::BatchInput, std::allocator<…> > const&, un…` | `libcorrectionlib.so` | 100.00% | 3.79% |
| NNJVT scale factor | small-R | inclusive | `[unknown]` | `_core.cpython-314-x86_64-linux-gnu.so` | 100.00% | 3.79% |
| NNJVT selection | small-R | self | `(anonymous namespace)::NnJvtSelect::evaluate_array(std::vector<std::variant<long, double, std::__cxx11::basic_s…` | `libjets.so` | 39.62% | 0.60% |
| NNJVT selection | small-R | self | `__gnu_cxx::__normal_iterator<float const*, std::vector<float, std::allocator<…> > > std::__lower_bound<__gnu_cx…` | `libjets.so` | 28.93% | 0.44% |
| NNJVT selection | small-R | inclusive | `correction::Correction::evaluate_batch_array(std::vector<correction::BatchInput, std::allocator<…> > const&, un…` | `libcorrectionlib.so` | 100.00% | 1.51% |
| NNJVT selection | small-R | inclusive | `[unknown]` | `_core.cpython-314-x86_64-linux-gnu.so` | 100.00% | 1.51% |
| Large-R selections | large-R | self | `[unknown]` | `libm.so.6` | 29.92% | 0.36% |
| Large-R selections | large-R | self | `expm1f32x` | `libm.so.6` | 18.90% | 0.23% |
| Large-R selections | large-R | inclusive | `correction::Correction::evaluate_batch_array(std::vector<correction::BatchInput, std::allocator<…> > const&, un…` | `libcorrectionlib.so` | 100.00% | 1.21% |
| Large-R selections | large-R | inclusive | `(anonymous namespace)::LargeSelection::evaluate_array(std::vector<std::variant<long, double, std::__cxx11::basi…` | `libjets.so` | 100.00% | 1.21% |
| Forward-folded JMR | large-R | self | `jets::portable::Histogram::GetBinContent(int) const` | `libjets.so` | 10.53% | 0.11% |
| Forward-folded JMR | large-R | self | `jets::portable::Axis::variable_bin(double) const` | `libjets.so` | 7.89% | 0.09% |
| Forward-folded JMR | large-R | inclusive | `correction::Correction::evaluate_batch_array(std::vector<correction::BatchInput, std::allocator<…> > const&, un…` | `libcorrectionlib.so` | 100.00% | 1.08% |
| Forward-folded JMR | large-R | inclusive | `[unknown]` | `_core.cpython-314-x86_64-linux-gnu.so` | 100.00% | 1.08% |
| Global sequential calibration | small-R | self | `jets::portable::Axis::variable_bin(double) const` | `libjets.so` | 29.63% | 0.23% |
| Global sequential calibration | small-R | self | `__gnu_cxx::__normal_iterator<double const*, std::vector<double, std::allocator<…> > > std::__lower_bound<__gnu_…` | `libjets.so` | 17.28% | 0.13% |
| Global sequential calibration | small-R | inclusive | `correction::Correction::evaluate_batch_array(std::vector<correction::BatchInput, std::allocator<…> > const&, un…` | `libcorrectionlib.so` | 100.00% | 0.77% |
| Global sequential calibration | small-R | inclusive | `[unknown]` | `_core.cpython-314-x86_64-linux-gnu.so` | 100.00% | 0.77% |
| Pileup truth labelling | shared | self | `[unknown]` | `libm.so.6` | 34.18% | 0.26% |
| Pileup truth labelling | shared | self | `expm1f32x` | `libm.so.6` | 21.52% | 0.16% |
| Pileup truth labelling | shared | inclusive | `correction::Correction::evaluate_batch_array(std::vector<correction::BatchInput, std::allocator<…> > const&, un…` | `libcorrectionlib.so` | 100.00% | 0.75% |
| Pileup truth labelling | shared | inclusive | `[unknown]` | `_core.cpython-314-x86_64-linux-gnu.so` | 100.00% | 0.75% |
| EtaJES | shared | self | `[unknown]` | `libm.so.6` | 44.62% | 0.28% |
| EtaJES | shared | self | `jets::portable::Histogram::GetBinContent(int) const` | `libjets.so` | 20.00% | 0.12% |
| EtaJES | shared | inclusive | `correction::Correction::evaluate_batch_array(std::vector<correction::BatchInput, std::allocator<…> > const&, un…` | `libcorrectionlib.so` | 100.00% | 0.62% |
| EtaJES | shared | inclusive | `(anonymous namespace)::EtaJES::evaluate_array(std::vector<std::variant<long, double, std::__cxx11::basic_string…` | `libjets.so` | 100.00% | 0.62% |
| Event scale factor | small-R | self | `(anonymous namespace)::EventSF::evaluate(std::vector<std::variant<long, double, std::__cxx11::basic_string<char…` | `libjets.so` | 80.00% | 0.30% |
| Event scale factor | small-R | self | `__tls_get_addr@plt` | `libjets.so` | 15.00% | 0.06% |
| Event scale factor | small-R | inclusive | `(anonymous namespace)::EventSF::evaluate(std::vector<std::variant<long, double, std::__cxx11::basic_string<char…` | `libjets.so` | 100.00% | 0.38% |
| Event scale factor | small-R | inclusive | `[unknown]` | `_core.cpython-314-x86_64-linux-gnu.so` | 100.00% | 0.38% |
| Pileup calibration | small-R | self | `(anonymous namespace)::PileupNode::evaluate_array(std::vector<std::variant<long, double, std::__cxx11::basic_st…` | `libjets.so` | 40.00% | 0.02% |
| Pileup calibration | small-R | self | `[unknown]` | `libm.so.6` | 20.00% | 0.01% |
| Pileup calibration | small-R | inclusive | `correction::Correction::evaluate_batch_array(std::vector<correction::BatchInput, std::allocator<…> > const&, un…` | `libcorrectionlib.so` | 100.00% | 0.05% |
| Pileup calibration | small-R | inclusive | `[unknown]` | `_core.cpython-314-x86_64-linux-gnu.so` | 100.00% | 0.05% |
| Nominal JMS | large-R | self | `jets::portable::Axis::variable_bin(double) const` | `libjets.so` | 60.00% | 0.03% |
| Nominal JMS | large-R | self | `int const& std::max<…>(int const&, int const&)` | `libjets.so` | 20.00% | 0.01% |
| Nominal JMS | large-R | inclusive | `correction::Correction::evaluate_batch_array(std::vector<correction::BatchInput, std::allocator<…> > const&, un…` | `libcorrectionlib.so` | 100.00% | 0.05% |
| Nominal JMS | large-R | inclusive | `[unknown]` | `_core.cpython-314-x86_64-linux-gnu.so` | 100.00% | 0.05% |
| Event inputs | shared | self | `(anonymous namespace)::EventInputs::evaluate_array(std::vector<std::variant<long, double, std::__cxx11::basic_s…` | `libjets.so` | 100.00% | 0.02% |
| Event inputs | shared | inclusive | `correction::Correction::evaluate_batch_array(std::vector<correction::BatchInput, std::allocator<…> > const&, un…` | `libcorrectionlib.so` | 100.00% | 0.02% |
| Event inputs | shared | inclusive | `[unknown]` | `_core.cpython-314-x86_64-linux-gnu.so` | 100.00% | 0.02% |

## Instrumented fresh-file phases

These single-pass diagnostics include interpreter startup and the saved histogram. Wall phases use exclusive hooks to avoid double counting nested calls. CPU time is the worker process clock, sampled before writing its diagnostic receipt. Tool rows include actual CorrectionLib dispatch plus any instrumented callees. Rows count tool inputs across calls, chunks and systematics. These measurements are separate from retained timing runs.

| Scope | 20,000-event wall s | Worker CPU s | Payload bytes if projected | NNJVT reuse |
| --- | --- | --- | --- | --- |
| Combined | 13.939 | 13.699 | Canonical | Active |
| Small-R | 11.860 | 11.673 | 35,330,047 | Active |
| Large-R | 2.990 | 2.851 | 40,518,516 | Inactive |

| Exclusive wall phase | Combined | Small-R | Large-R |
| --- | --- | --- | --- |
| Startup through CLI entry | 0.144 | 0.167 | 0.144 |
| Calibration setup | 1.188 | 0.551 | 0.640 |
| Open, branch selection, read and decode | 1.260 | 1.168 | 0.740 |
| Python workflow and dispatch | 1.514 | 1.327 | 0.267 |
| CorrectionLib tool calls | 9.237 | 8.169 | 1.043 |
| Transport bindings | 0.062 | 0.061 | 0.002 |
| Histogram operations | 0.383 | 0.294 | 0.035 |
| Output and runtime audit | 0.004 | 0.003 | 0.003 |
| Teardown after CLI | 0.000 | 0.000 | 0.000 |
| Remaining phase overhead | 0.147 | 0.120 | 0.116 |
| External wall total | 13.939 | 11.860 | 2.990 |

| Startup or remainder detail | Combined | Small-R | Large-R |
| --- | --- | --- | --- |
| Worker bootstrap before visible script | 0.005 | 0.005 | 0.006 |
| Visible import through CLI entry | 0.139 | 0.162 | 0.138 |
| Compiler runtime within visible import | 0.001 | 0.002 | 0.001 |
| Diagnostic receipt and other wall time outside the observed worker interval | 0.147 | 0.120 | 0.116 |

The detail rows break out portions of startup and remainder already included in the exclusive wall table.

### Combined correction calls

| Correction node | Calls | Rows | Wall s | Worker CPU s |
| --- | --- | --- | --- | --- |
| `small_uncertainty` | 2,340 | 23,002,902 | 4.479 | 4.454 |
| `small_nnjvt_update` | 2,180 | 16,070,813 | 2.070 | 2.058 |
| `small_nnjvt_sf` | 2,380 | 23,396,114 | 0.799 | 0.795 |
| `large_uncertainty` | 3,660 | 4,058,391 | 0.651 | 0.650 |
| `small_nnjvt_select` | 2,340 | 23,002,902 | 0.478 | 0.476 |
| `large_selection` | 4,380 | 4,856,763 | 0.229 | 0.228 |
| `large_jmr` | 720 | 798,372 | 0.161 | 0.160 |
| `jet_pileup_truth` | 40 | 218,783 | 0.100 | 0.100 |
| `small_gsc` | 20 | 196,606 | 0.096 | 0.096 |
| `jet_event_sf` | 2,380 | 2,380,000 | 0.089 | 0.089 |
| `small_eta_jes` | 20 | 196,606 | 0.056 | 0.056 |
| `large_eta_jes` | 20 | 22,177 | 0.010 | 0.010 |
| `small_pileup` | 20 | 196,606 | 0.010 | 0.009 |
| `large_jms` | 20 | 22,177 | 0.005 | 0.005 |
| `jet_event_inputs` | 20 | 20,000 | 0.003 | 0.003 |

### Small-R correction calls

| Correction node | Calls | Rows | Wall s | Worker CPU s |
| --- | --- | --- | --- | --- |
| `small_uncertainty` | 2,340 | 23,002,902 | 4.442 | 4.418 |
| `small_nnjvt_update` | 2,180 | 16,070,813 | 2.085 | 2.076 |
| `small_nnjvt_sf` | 2,380 | 23,396,114 | 0.810 | 0.807 |
| `small_nnjvt_select` | 2,340 | 23,002,902 | 0.483 | 0.481 |
| `jet_pileup_truth` | 20 | 196,606 | 0.097 | 0.097 |
| `small_gsc` | 20 | 196,606 | 0.095 | 0.095 |
| `jet_event_sf` | 2,380 | 2,380,000 | 0.091 | 0.090 |
| `small_eta_jes` | 20 | 196,606 | 0.054 | 0.053 |
| `small_pileup` | 20 | 196,606 | 0.010 | 0.010 |
| `jet_event_inputs` | 20 | 20,000 | 0.003 | 0.003 |

### Large-R correction calls

| Correction node | Calls | Rows | Wall s | Worker CPU s |
| --- | --- | --- | --- | --- |
| `large_uncertainty` | 915 | 4,058,391 | 0.581 | 0.579 |
| `large_selection` | 1,095 | 4,856,763 | 0.221 | 0.215 |
| `large_jmr` | 180 | 798,372 | 0.221 | 0.219 |
| `large_eta_jes` | 5 | 22,177 | 0.007 | 0.007 |
| `jet_pileup_truth` | 5 | 22,177 | 0.006 | 0.006 |
| `large_jms` | 5 | 22,177 | 0.004 | 0.004 |
| `jet_event_inputs` | 5 | 20,000 | 0.002 | 0.002 |

## Installed combined Python call profile

One cProfile pass ran the delivered full-systematics defaults on the original 20,000-event file. It physically mapped the source and installed runtime on CPU 3 with one analysis thread. Every saved histogram field matched independent stock. The process took 17.137 s wall. The profile recorded 16.986 s across 14,761,380 calls. Self time excludes recorded callees and can include native work in a Python binding. Cumulative rows include callees and can overlap. This diagnostic sits outside retained timing.

| Measured function | Function | Calls | Self s | Cumulative s |
| --- | --- | --- | --- | --- |
| CorrectionLib dispatch | `highlevel.py:194 _evaluate` | 20,540 | 9.006 | 10.050 |
| NumPy flatten in CorrectionLib input dispatch | `<method 'flatten' of 'numpy.ndarray' objects>` | 129,220 | 0.295 | 0.295 |
| NumPy astype | `<method 'astype' of 'numpy.ndarray' objects>` | 22,780 | 0.055 | 0.055 |
| NumPy where dispatch hook | `multiarray.py:406 where` | 22,180 | 0.002 | 0.002 |
| Status conversion | `jets_demo.py:183 status_bits` | 7,480 | 0.162 | 0.240 |
| Per-chunk evaluation | `jets_demo.py:313 evaluate_chunk` | 6,780 | 0.064 | 11.644 |
| NNJVT selection | `jets_demo.py:275 small_jvt_selection` | 2,340 | 0.119 | 3.258 |
| NNJVT update orchestration | `jets_demo.py:255 evaluate` | 2,340 | 0.224 | 2.554 |
| NNJVT scale-factor orchestration | `jets_demo.py:296 small_sf` | 2,380 | 0.053 | 1.184 |
| Histogram façade | `basehist.py:328 fill` | 6,760 | 0.048 | 0.630 |
| Histogram fill implementation | `histogram.py:922 fill` | 6,760 | 0.252 | 0.290 |
| JSON decoder across all callers | `decoder.py:351 raw_decode` | 366 | 0.350 | 0.350 |
| Native CorrectionLib parse and construction | `<built-in method correctionlib._core.from_string>` | 1 | 0.870 | 0.870 |

Each caller row measures a direct call edge and contributes to the function totals above. The table shows up to three callers per selected function. The NumPy `where` row measures its Python dispatch hook, with no separately identified native kernel time.

| Invoked function | Direct caller | Calls | Self s | Cumulative s |
| --- | --- | --- | --- | --- |
| NumPy flatten in CorrectionLib input dispatch | `highlevel.py:231 <genexpr>` | 129,220 | 0.295 | 0.295 |
| NumPy astype | `jets_demo.py:313 evaluate_chunk` | 6,800 | 0.023 | 0.023 |
| NumPy astype | `jets_demo.py:275 small_jvt_selection` | 7,020 | 0.021 | 0.021 |
| NumPy astype | `jets_demo.py:183 status_bits` | 7,480 | 0.007 | 0.007 |
| NumPy where dispatch hook | `jets_demo.py:183 status_bits` | 14,960 | 0.002 | 0.002 |
| NumPy where dispatch hook | `jets_demo.py:275 small_jvt_selection` | 7,020 | 0.001 | 0.001 |
| NumPy where dispatch hook | `array_module.py:493 where` | 160 | 0.000 | 0.000 |
| Status conversion | `jets_demo.py:313 evaluate_chunk` | 7,480 | 0.162 | 0.240 |
| NNJVT update orchestration | `jets_demo.py:275 small_jvt_selection` | 2,340 | 0.224 | 2.554 |
| Histogram façade | `jets_demo.py:482 main` | 6,760 | 0.048 | 0.630 |

The direct `plugins.prepare → json.loads` call took 0.349 s of 0.352 s across all `json.loads` calls (99.01%). Plugin preparation took 0.368 s including Python parsing and the validation walk. Native parsing and construction are measured separately above.

The visible input helper `atlas_jet_demo.inputs.flatten` made 820 calls (0.001 s self, 0.090 s cumulative). The NumPy flatten row above measures calls directly under CorrectionLib's high-level dispatcher.

## Matched native sampling overhead diagnostic

The recorded and unprofiled commands used the same installed script, runtime libraries, physical branches and 10 visits to the original file. Both saved histograms matched independent stock in every field. The recorded process wall is bounded by the last pass receipt and the duration of the enclosing recorder stage.

| Boundary | Wall s |
| --- | --- |
| Profiled lower bound through last pass receipt | 119.233 |
| Profiled upper bound through recorder stage exit | 120.076 |
| Unprofiled worker process start to exit | 119.556 |

Profiled minus unprofiled wall for this pair lies between -0.32 and +0.52 s. The lower bound ends before output and teardown. The upper bound includes controller metadata and checks. The interval spans zero. Run-to-run variation also contributes to the observed difference. This diagnostic pair sits outside formal timing.

[Recording and pass receipts](evidence/final/native/recording.json) · [Decoded profile](evidence/final/native/summary.json) · [Owners](evidence/final/native/owners.tsv) · [Global self](evidence/final/native/self.tsv) · [Global inclusive](evidence/final/native/inclusive.tsv) · [Within-tool self](evidence/final/native/within_owner_self.tsv) · [Within-tool inclusive](evidence/final/native/within_owner_inclusive.tsv) · [Instrumented phases](evidence/final/phases/summary.json) · [Phase provenance](evidence/final/phases/provenance.json) · [Python call and caller summary](evidence/final/python-profile/summary.json) · [Python executable and source provenance](evidence/final/python-profile/provenance.json) · [Python process audit](evidence/final/python-profile/visible.json) · [Python exact histogram proof](evidence/final/python-profile/histogram-comparison.json) · [Matched unprofiled proof](evidence/final/native-unprofiled/diagnostic.json) · [Matched visible commands](evidence/final/native-unprofiled/command.json) · [Recorder stage start](evidence/final/controller/01-native-record/started.utc) · [Recorder stage end](evidence/final/controller/01-native-record/ended.utc)
