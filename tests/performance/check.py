#!/usr/bin/env python3
"""Reproducible NumCalc regression checks; EUPL-1.2, 2026-10-12."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

import numpy as np

from sphere import sphere_mesh


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "mesh2hrtf/NumCalc/src"
BASE = "e45d0436a6fbeca3db13828cbae23ca109225be3"


def run(command, cwd, log, **kwargs):
    with log.open("w") as handle:
        subprocess.run(command, cwd=cwd, stdout=handle,
                       stderr=subprocess.STDOUT, check=True, timeout=180,
                       **kwargs)


def build(source, destination, cxx, velocity=None):
    src = destination / "src"
    src.mkdir(parents=True)
    (destination / "bin").mkdir()
    for path in source.iterdir():
        if path.suffix in (".cpp", ".h") or path.name == "Makefile":
            shutil.copy2(path, src / path.name)
    args = ["make", "-j4", "CC=" + cxx, "CXX=" + cxx,
            "OPTIM=-O2 -DNDEBUG"]
    if velocity is not None:
        args.append("EVALUATION_VELOCITY=" + str(velocity))
    run(args, src, destination / "build.log")
    return destination / "bin/NumCalc"


def export_reference(destination):
    destination.mkdir()
    prefix = "mesh2hrtf/NumCalc/src/"
    names = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", BASE, prefix],
        cwd=ROOT, text=True).splitlines()
    for name in names:
        if Path(name).suffix in (".cpp", ".h") or name.endswith("/Makefile"):
            (destination / Path(name).name).write_bytes(
                subprocess.check_output(["git", "show", BASE + ":" + name],
                                        cwd=ROOT))
    return destination


def check_ilu(reference, candidate, folder, cxx):
    folder.mkdir()
    src = reference / "src"
    renamed = folder / "main_renamed.o"
    flags = ["-std=c++11", "-O2", "-DNDEBUG", "-fopenmp", "-I", str(src)]
    run([cxx, *flags, "-Dmain=numcalc_original_main", "-c",
         str(src / "NC_Main.cpp"), "-o", str(renamed)],
        folder, folder / "build-main.log")
    shared = [str(p) for p in sorted(src.glob("*.o"))
              if p.name not in ("NC_Main.o", "NC_CommonFunctions.o")]
    binaries = {}
    for name, common in (("reference", src / "NC_CommonFunctions.o"),
                         ("candidate", candidate / "src/NC_CommonFunctions.o")):
        binary = folder / name
        run([cxx, *flags, str(Path(__file__).with_name("ilu_probe.cpp")),
             *shared, str(renamed), str(common), "-o", str(binary)],
            folder, folder / ("build-" + name + ".log"))
        binaries[name] = binary

    random = np.random.default_rng(739102)
    requests, cases = [], []
    for n in (7, 31, 97, 257):
        for method in (0, 1, 3):
            for degree in (0, 1, 2, 3):
                cols, values, ptr = [], [], [0]
                for i in range(n):
                    indices = (np.arange(n) if method == 0 else np.unique(
                        np.r_[i, random.choice(n, size=min(n, 17), replace=False)]))
                    if method:
                        random.shuffle(indices)
                        if degree == 3 and len(indices) > 2:
                            indices = np.r_[indices, indices[0]]
                    for j in indices:
                        cols.append(int(j))
                        values.append(complex(6 + random.random(), .15) if i == j
                                      else complex(random.normal(), random.normal()))
                    ptr.append(len(cols))
                rhs = random.normal(size=n) + 1j * random.normal(size=n)
                tokens = [len(cases), n, method, degree, len(cols), *ptr, *cols]
                tokens += [v for z in values for v in (z.real, z.imag)]
                tokens += [v for z in rhs for v in (z.real, z.imag)]
                requests.append(" ".join(format(x, ".17g") for x in tokens) + "\n")
                cases.append({"size": n, "method": method, "degree": degree})
    outputs = {}
    for name, binary in binaries.items():
        proc = subprocess.run([str(binary)], input="".join(requests), text=True,
                              cwd=folder, capture_output=True, check=True,
                              timeout=180, env=environment(1))
        (folder / (name + ".txt")).write_text(proc.stdout)
        (folder / (name + ".log")).write_text(proc.stderr)
        assert not re.search(r"(?i)\b(?:nan|inf)\b", proc.stdout)
        outputs[name] = proc.stdout
    assert outputs["reference"] == outputs["candidate"], "ILU factors or solve differ"
    print("ILU: 48 exact pattern/factor/solve comparisons passed", flush=True)
    return {"passed": True, "cases": cases,
            "output_sha256": hashlib.sha256(outputs["reference"].encode()).hexdigest()}


def environment(threads):
    return dict(os.environ, OMP_NUM_THREADS=str(threads), OMP_DYNAMIC="FALSE",
                OMP_MAX_ACTIVE_LEVELS="1", OMP_PROC_BIND="spread",
                OMP_PLACES="cores", OMP_WAIT_POLICY="PASSIVE")


def sphere_case(folder, method, radius, beta):
    folder.mkdir(parents=True)
    vertices, faces = sphere_mesh()
    directions, eval_faces = sphere_mesh(0)
    for name, nodes, elements, offset, element_offset, attribute in (
        ("ObjectMeshes", vertices * .1, faces, 0, 0, "0 0 0"),
        ("EvaluationGrids", directions * radius, eval_faces, 100000, 200000, "2 0 1"),
    ):
        dest = folder / name
        dest.mkdir()
        (dest / "Nodes.txt").write_text(str(len(nodes)) + "\n" + "".join(
            f"{i+offset} {p[0]:.17e} {p[1]:.17e} {p[2]:.17e}\n"
            for i, p in enumerate(nodes)))
        (dest / "Elements.txt").write_text(str(len(elements)) + "\n" + "".join(
            f"{i+element_offset} {p[0]+offset} {p[1]+offset} {p[2]+offset} {attribute}\n"
            for i, p in enumerate(elements)))
    text = f"""## Synthetic pulsating sphere regression
Mesh2HRTF 1.3.0
##
Pulsating sphere with additive complex admittance
## Controlparameter I
0 0 0 0 7 0
## Controlparameter II
1 1 0.000001 0.00e+00 1 0 0
## Load Frequency Curve
0 2
0.000000 0.0 0.0
0.000001 1000.0 0.0
## 1. Main Parameters I
2 {len(faces)+len(eval_faces)} {len(vertices)+len(directions)} 0 0 2 1 {method} 0
## 2. Main Parameters II
0 0 0 0.0 -1 0 0
## 3. Main Parameters III
0 0 0 0
## 4. Main Parameters IV
343.18 1.1839 1.0 0.0 0.0 0.0 0.0
NODES
ObjectMeshes/Nodes.txt
EvaluationGrids/Nodes.txt
ELEMENTS
ObjectMeshes/Elements.txt
EvaluationGrids/Elements.txt
BOUNDARY
ELEM 0 TO {len(faces)-1} VELO 0.1 -1 0.0 -1
"""
    if beta:
        text += f"ELEM 0 TO {len(faces)-1} ADMI {beta.real} -1 {beta.imag} -1\n"
    (folder / "NC.inp").write_text(text + "RETU\nPOST PROCESS\nEND\n")


def execute(binary, folder, threads):
    run([str(binary), "-istart", "1", "-iend", "1", "-nitermax", "1000"],
        folder, folder / "stdout.log", env=environment(threads))
    assert "End time:" in (folder / "NC1-1.out").read_text()
    return (folder / "stdout.log").read_text()


def check_spheres(binaries, work, thread_counts):
    results = []
    for method in (0, 1, 4):
        for radius in (.12, 1.5):
            for material, beta in (("rigid", 0j), ("positive", .2+.15j),
                                   ("negative", .2-.15j)):
                key = f"m{method}-r{radius}-{material}"
                ref = work / "spheres" / key / "reference"
                sphere_case(ref, method, radius, beta)
                execute(binaries["reference"], ref, 1)
                for mode in ("pressure", "velocity"):
                    for threads in thread_counts:
                        dest = ref.parent / f"{mode}-{threads}"
                        dest.mkdir()
                        for name in ("ObjectMeshes", "EvaluationGrids"):
                            shutil.copytree(ref / name, dest / name)
                        shutil.copy2(ref / "NC.inp", dest / "NC.inp")
                        # A previous velocity run must not leave misleading output.
                        if mode == "pressure":
                            stale = dest / "be.out/be.1/vEvalGrid"
                            stale.parent.mkdir(parents=True)
                            stale.write_text("stale evaluation velocity\n")
                        log = execute(binaries[mode], dest, threads)
                        fields = ["pEvalGrid", "pBoundary", "vBoundary"]
                        if mode == "velocity":
                            fields.append("vEvalGrid")
                        for field in fields:
                            assert ((ref / "be.out/be.1" / field).read_bytes() ==
                                    (dest / "be.out/be.1" / field).read_bytes()), (key, mode, threads, field)
                        assert (dest / "be.out/be.1/vEvalGrid").exists() == (mode == "velocity")
                        match = re.search(r"MRADM_EVAL far_pairs (\d+) near_pairs (\d+) threads (\d+)", log)
                        if method:
                            assert match and int(match[3]) == threads, (key, mode, threads)
                        if method == 4 and radius == .12:
                            assert int(match[2]) > 0
                        results.append({"case": key, "mode": mode, "threads": threads,
                                        "fields_byte_identical": fields,
                                        "near_pairs": int(match[2]) if match else None})
                print("Sphere:", key, "passed", flush=True)
    return results


def check_cleanup(work):
    path = ROOT / "mesh2hrtf/Output2HRTF/remove_outputs.py"
    spec = importlib.util.spec_from_file_location("remove_outputs", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for velocity in (False, True):
        project = work / f"cleanup-{velocity}"
        folder = project / "NumCalc/source_1/be.out/be.1"
        folder.mkdir(parents=True)
        for name in ("pBoundary", "vBoundary", "pEvalGrid"):
            (folder / name).write_text("fixture")
        if velocity:
            (folder / "vEvalGrid").write_text("fixture")
        module.remove_outputs(str(project), grid=True)
        assert sorted(p.name for p in folder.iterdir()) == ["pBoundary", "vBoundary"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument("--reference-source", type=Path)
    parser.add_argument("--cxx", default="g++")
    parser.add_argument("--threads", nargs="+", type=int, default=[1, 8])
    args = parser.parse_args()
    if not args.threads or min(args.threads) < 1:
        parser.error("thread counts must be positive")
    work = args.work_dir.resolve()
    work.mkdir(parents=True, exist_ok=False)
    reference = (args.reference_source.resolve() if args.reference_source else
                 export_reference(work / "reference-source"))
    binaries = {"reference": build(reference, work / "reference", args.cxx)}
    for name, velocity in (("pressure", 0), ("velocity", 1)):
        binaries[name] = build(SOURCE, work / name, args.cxx, velocity)
    ilu = check_ilu(work / "reference", work / "pressure", work / "ilu", args.cxx)
    spheres = check_spheres(binaries, work, args.threads)
    check_cleanup(work)
    report = {"passed": True, "reference_commit": BASE,
              "compiler": subprocess.check_output([args.cxx, "--version"], text=True).splitlines()[0],
              "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in sorted(SOURCE.glob("NC_*.cpp"))},
              "ilu": ilu, "spheres": spheres, "pressure_only_cleanup": True}
    (work / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"PASS: 48 ILU cases, {len(spheres)} sphere comparisons, output cleanup", flush=True)


if __name__ == "__main__":
    main()
