# NumCalc performance regression checks

These tests build the current solver and the pinned Mesh2HRTF v1.3.0 reference
(`e45d0436a6fbeca3db13828cbae23ca109225be3`) with the same compiler. They use
generated data and require Python 3, NumPy, GNU Make, and GCC with OpenMP.

From the repository root:

```sh
python3 tests/performance/check.py --work-dir /tmp/mesh2hrtf-perf-check
```

The work directory must not already exist. The script exports only the small
NumCalc source directory from Git; it does not clone another repository or
download head meshes. Build output, solver logs, and `report.json` stay in that
directory. `--reference-source /path/to/v1.3.0/NumCalc/src` can supply the exact
reference sources on a machine without the Git checkout. `--cxx g++` selects the
compiler. Both versions must use the same compiler and floating-point flags.

Coverage:

- 48 ILU inputs: sizes 7, 31, 97, and 257; TBEM, SLFMM, and direct MLFMM;
  scanning degrees 0–3; unsorted sparse rows and duplicate columns. Compare every
  L/U index, factor, and preconditioner result at 17 significant digits.
- Pulsating sphere (512 triangles): rigid boundary and complex admittance with
  both signs of the imaginary part; TBEM, SLFMM, and direct MLFMM; evaluation
  radii 0.12 m and 1.5 m around a 0.1 m sphere; one and eight threads.
- Byte-for-byte comparison of `pEvalGrid`, `pBoundary`, and `vBoundary` against
  the reference. Velocity-enabled builds also compare `vEvalGrid`. Default
  pressure-only builds must omit that file in fresh output directories.
- The direct MLFMM near-evaluation cases must exercise the near integration
  path. OpenMP diagnostics must report the requested team size for FMM cases.
- 24 additional comparisons cover mixed triangle/quadrilateral meshes,
  reflected clusters, adaptive expansion on/off, and a 1/4/1 kHz sequence in
  the same process. All cases also compare iteration counts and residuals.

For bounded Linux timings, `benchmark.py` accepts a solver executable, an
input-only project template, a reference `be.out/be.1` directory, and a fresh
work directory. The template contains `NumCalc/source_1/NC.inp`; shared geometry
may be symlinked. It supports `--processes`, `--threads`, and `--copies`, assigns
disjoint CPU sets, checks field hashes and convergence, and writes `report.json`.
Set `--expected-rss-gib` to reserve memory per process; the default total memory
ceiling is 112 GiB. A `STOP` file in the work directory terminates only that
benchmark's child processes. `--pause-control` can point to a campaign JSON file
whose `allow_fullband` must remain false. The helper requires `psutil` and
Linux `taskset`; it never changes the production campaign state.

These are correctness checks, not speed benchmarks. They do not establish
convergence of a particular head mesh or guarantee identical output across
different compilers, CPUs, or floating-point options.
