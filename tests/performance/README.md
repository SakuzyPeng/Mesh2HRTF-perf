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

These are correctness checks, not speed benchmarks. They do not establish
convergence of a particular head mesh or guarantee identical output across
different compilers, CPUs, or floating-point options.
