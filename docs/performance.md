# Mesh2HRTF-perf

This fork contains NumCalc performance work based on Mesh2HRTF **v1.3.0**, commit
[`e45d0436a6fbeca3db13828cbae23ca109225be3`](https://github.com/Any2HRTF/Mesh2HRTF/commit/e45d0436a6fbeca3db13828cbae23ca109225be3).
The changes are dated **2026-10-12**. The original [EUPL-1.2 license](../LICENSE.txt),
source authorship notices, references, and upstream history are retained.

## Changes

- Sparse ILU setup uses a stable counting transpose, sorted unique row patterns,
  and sparse intersections instead of repeated dense scans. Thresholds, scaling,
  pivot order, duplicate-column first-match behavior, and subtraction order are
  preserved.
- OpenMP parallelizes independent matrix-vector rows and partitions them by
  nonzero count. Row summation order, FMM level order, triangular solves, and CGS
  reductions remain unchanged.
- Near-field assembly distributes element clusters across threads with private
  integration scratch state. Each cluster owns its output rows.
- Postprocessing computes only the coarsest T vector consumed by the evaluation
  routine and parallelizes independent evaluation-point clusters.
- The default HRTF build computes evaluation-grid pressure only. It retains
  boundary velocity required for pressure and both boundary output files.

The numerical integration rules, mesh, material parameters, and convergence
criteria are unchanged. This work does not resolve or diagnose mesh-convergence
differences at 16 kHz.

## Build and run

The validated platform is **Linux x86-64, GCC 11.4.0, OpenMP**. NumCalc remains
C++11. No new Python dependency is needed to build the solver.

```sh
make -C mesh2hrtf/NumCalc/src -j8
```

Run `mesh2hrtf/NumCalc/bin/NumCalc` from a NumCalc source directory containing
`NC.inp`. For example, if `NUMCALC` is set to the absolute path of that executable:

```sh
export OMP_NUM_THREADS=8
export OMP_DYNAMIC=FALSE
export OMP_MAX_ACTIVE_LEVELS=1
export OMP_PROC_BIND=spread
export OMP_PLACES=cores
export OMP_WAIT_POLICY=PASSIVE
"$NUMCALC" -istart 1 -iend 1
```

The executable keeps the upstream name `NumCalc`. `MRADM_PERF`, `MRADM_ILU`,
`MRADM_ROW`, `MRADM_REGION`, `MRADM_EVAL`, and `MRADM_OUTPUT` diagnostics on stderr
record solver phases and observed OpenMP teams. They are included in the
reported timings. Row timing samples are limited to the first 24 warmed calls
and 128 threads; that sampling limit does not limit the solver team size.

Set `OMP_NUM_THREADS` explicitly. NumCalc's process-level scheduler was not
changed to account for threads: the product of concurrent processes and threads
per process should fit the available CPUs, with enough memory for each process.
The benchmark below measures one process, not multi-process throughput.

### Output policy

Default `EVALUATION_VELOCITY=0` writes `pEvalGrid`, `pBoundary`, and `vBoundary`.
It omits evaluation-grid velocity and intensity calculations and removes an old
`vEvalGrid` for a frequency being recomputed. It does not write placeholder
velocities. The Python `remove_outputs(..., grid=True)` helper accepts this
missing optional velocity file.

Applications requiring evaluation-grid velocity can rebuild with:

```sh
make -C mesh2hrtf/NumCalc/src clean
make -C mesh2hrtf/NumCalc/src -j8 EVALUATION_VELOCITY=1
```

Run `make clean` before changing build flags or switching output modes. The
velocity-enabled build is checked on synthetic fixtures; the reported full-head
timings for the combined optimization use pressure-only mode. Downstream tools
that explicitly request `vEvalGrid` require the velocity-enabled build.

`CXX`, `OPTIM`, `CPPFLAGS`, `CXXFLAGS`, `LDFLAGS`, `LDLIBS`, and `OPENMP_FLAGS` can
be overridden. Apple Clang needs an OpenMP runtime and appropriate flags; the
upstream Visual Studio project is not updated or validated for these changes.
No macOS or Windows performance claim is made by this fork.

## Recorded measurements

One left-ear HRTF source on a 69,270-triangle head mesh with complex skin RLC
admittance was tested on an Intel Xeon Platinum 8352V. Builds used `-O2 -DNDEBUG`
without fast-math. The four 4 kHz configurations below ran sequentially with the
same eight-CPU affinity set. Each configuration was timed once.

| Configuration | Threads | 4 kHz wall time | Ratio to serial control |
| --- | ---: | ---: | ---: |
| v1.3.0 serial control with timing instrumentation | 1 | 366.10 s | 1.00× |
| Sparse ILU + balanced matrix-vector multiplication | 8 | 120.20 s | 3.05× |
| Combined changes, pressure-only output | 1 | 227.90 s | 1.61× |
| Combined changes, pressure-only output | 8 | 50.59 s | 7.24× |

The combined build used approximately **3.09 GiB** peak RSS at 4 kHz. Pressure
and both boundary output files matched the original reference byte for byte;
the 201 iterations and reported residual `2.66821e-10` were unchanged. The ratio
includes algorithmic changes and omitted velocity work as well as parallelism;
it is not a pure eight-thread scaling factor. Within the combined build, the
observed one-to-eight-thread wall-time ratio was **4.50×**.

Selected phase timings explain the gains: the measured ILU setup fell from
131.99 s to roughly 0.9 s after replacing dense scans. Near assembly fell from
69.76 s to 9.89 s, and evaluation postprocessing from 7.71 s to 1.00 s. These
phase comparisons use the corresponding instrumented controls.

At **24 kHz**, the combined eight-thread build completed in **908.08 s
(15.13 min)**, using approximately **24.31 GiB** peak RSS. Pressure and both
boundary files again matched the original reference byte for byte; the 501
iterations and residual `5.77474e-10` were unchanged. The historical original
run took 4,766.12 s while other frequencies were running concurrently. That
historical ratio is **not a matched-condition speedup benchmark**.

Machine-readable, path-free measurements are in
[`benchmarks/numcalc-2026-10-12.json`](../benchmarks/numcalc-2026-10-12.json).
Head geometry, raw personal HRTFs, and machine access details are not included.
These measurements do not establish whole-band throughput, repeated-run
variance, or speed on other hosts.

## Validation

The experimental build was compared against the original solver at 4 kHz and
24 kHz, plus far- and near-field synthetic sphere cases with rigid and complex
admittance boundaries. All compared pressure and boundary files were identical.
An additional 48-matrix test checked all ILU indices, factors, and preconditioner
application results at 17 significant digits, including unsorted and duplicate
sparse columns.

The packaged sources add build configuration, modification notices, and stale
velocity-file handling to that validated numerical code. The portable
[`tests/performance`](../tests/performance/README.md) checks rebuild both output
modes and the pinned upstream solver and compare TBEM, SLFMM, and direct MLFMM
results on generated spheres. They also test ILU parity and output cleanup. On GCC 11.4.0, all 48 ILU cases,
72 sphere comparisons, and cleanup checks passed; the
[packaged validation record](../benchmarks/packaged-validation-2026-10-12.json)
contains the tested source hashes and case results.
They do not require a personal mesh or a remote account.

Matching the reference verifies preservation on the tested inputs; it is not a
general proof of numerical accuracy, mesh convergence, or thread safety for
every boundary condition. No production full-band run has been completed with
this fork yet.


## Follow-up: parallel D assembly

The D-matrix builder now obtains each cluster's destination block from its CSR
row pointers and distributes clusters across OpenMP threads. Hankel, Legendre,
and direction scratch are private to each worker; levels and within-entry
summation order remain unchanged. CSR block sizes are checked before entering
the parallel region.

A new isolated comparison against commit `9b386dc` used the same GCC 11.4.0
build settings, eight-CPU affinity, input, and output mode:

| Frequency | Baseline | Parallel D | Whole-job improvement | Samples per variant |
| --- | ---: | ---: | ---: | ---: |
| 4 kHz | 50.63 s | 48.21 s | 4.8% | 3, median |
| 24 kHz | 916.77 s | 776.99 s | 15.2% | 1 |

The 4 kHz D-assembly median fell from 2.98 s to 0.39 s. All pressure and boundary
files, iteration counts, and residuals matched the reference. The 24 kHz result
is a single-run stage check; final repeated high-frequency validation follows
after the remaining experiments.

Validation includes 48 ILU cases, 72 existing sphere comparisons, 24 additional
mixed-element/reflection/adaptive/multiple-frequency comparisons, and four
benchmark resource/cleanup guard tests. Full measurements and source hashes are
in [the D-stage record](../benchmarks/parallel-d-2026-10-12.json).


## Follow-up: parallel T assembly

T-matrix and incident T-vector assembly now assign each cluster its own CSR
block. Gaussian-rule scratch is thread-local and reset for each cluster;
within-cluster element and integration order are unchanged. Each cluster's
final address is verified after assembly.

Against the preceding D-assembly version:

| Frequency | Parallel D | Parallel D + T | Whole-job improvement | Samples per variant |
| --- | ---: | ---: | ---: | ---: |
| 4 kHz | 47.82 s | 46.21 s | 3.4% | 3, median |
| 24 kHz | 834.79 s | 732.39 s | 12.3% | 1 |

All field bytes and convergence records matched, including the 48 ILU,
72 sphere, and 24 extended regression comparisons. High-frequency whole-job
times varied between runs of the same control binary; these stage measurements
remain single-run observations pending the final three-pair comparison.
See [the T-stage record](../benchmarks/parallel-t-2026-10-12.json) for phase times,
source hashes, and all samples.
