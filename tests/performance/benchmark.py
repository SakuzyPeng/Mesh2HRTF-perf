#!/usr/bin/env python3
"""Bounded Linux NumCalc single-process/throughput benchmark. EUPL-1.2."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import time

import psutil


GIB = 1024**3
FIELDS = ("pEvalGrid", "pBoundary", "vBoundary")
CGS = r"CGS solver: number of iterations\s*=\s*(\d+), relative error\s*=\s*([0-9.eE+\-]+)"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def memory_gib():
    path = Path("/sys/fs/cgroup/memory.current")
    return int(path.read_text()) / GIB if path.exists() else psutil.virtual_memory().used / GIB


def stop(jobs):
    for job in jobs:
        if job["process"].poll() is None:
            try:
                os.killpg(job["process"].pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
    for job in jobs:
        try:
            job["process"].wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(job["process"].pid, signal.SIGKILL)
            job["process"].wait()
        job["handle"].close()


def interrupted(signum, frame):
    raise InterruptedError(f"Benchmark interrupted by signal {signum}")


def environment(threads, malloc_arenas=None):
    env = dict(os.environ, OMP_NUM_THREADS=str(threads), OMP_DYNAMIC="FALSE",
               OMP_MAX_ACTIVE_LEVELS="1", OMP_PROC_BIND="spread", OMP_PLACES="cores",
               OMP_WAIT_POLICY="PASSIVE")
    if malloc_arenas is not None:
        env["MALLOC_ARENA_MAX"] = str(malloc_arenas)
    return env


def run_batch(args):
    work = args.work_dir.resolve()
    work.mkdir(parents=True, exist_ok=False)
    solver = args.solver.resolve()
    cpus = sorted(os.sched_getaffinity(0))
    if args.processes * args.threads > len(cpus):
        raise ValueError("Requested teams exceed the allowed CPU set")
    if args.pause_control and json.loads(args.pause_control.read_text())["allow_fullband"]:
        raise ValueError("Production full-band dispatch must remain paused")
    if memory_gib() + args.processes * args.expected_rss_gib * 1.05 > args.memory_limit_gib:
        raise ValueError("Insufficient memory headroom for this batch")
    expected = {name: sha(args.reference_dir / name) for name in FIELDS}
    expected_cgs = re.findall(CGS, (args.reference_dir.parent.parent / "NC1-1.out").read_text())
    assert len(expected_cgs) == 1, "Reference must contain one completed solve"
    assert float(expected_cgs[0][1]) < 1e-9, "Reference solve did not converge"
    template = args.template.resolve()
    active, results, slots = [], [], list(range(args.processes))
    begin, next_job, peak_total, peak_rss = time.monotonic(), 0, memory_gib(), 0.0
    count = args.copies
    report = {"passed": False, "solver_sha256": sha(solver),
              "input_sha256": sha(template / "NumCalc/source_1/NC.inp"),
              "processes": args.processes, "threads": args.threads, "copies": count,
              "memory_limit_gib": args.memory_limit_gib,
              "malloc_arena_max": environment(args.threads, getattr(args, "malloc_arenas", None)).get("MALLOC_ARENA_MAX"),
              "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    last_status = 0.0
    old_handler = signal.signal(signal.SIGTERM, interrupted)
    try:
        while len(results) < count:
            if (work / "STOP").exists():
                raise RuntimeError("Benchmark stop requested")
            if args.pause_control and json.loads(args.pause_control.read_text())["allow_fullband"]:
                raise RuntimeError("Production dispatch became enabled")
            used = memory_gib()
            peak_total = max(peak_total, used)
            if used > args.memory_limit_gib:
                raise RuntimeError("Memory limit exceeded")
            while slots and next_job < count:
                slot = slots.pop(0)
                folder = work / f"job-{next_job:02d}"
                shutil.copytree(template, folder, symlinks=True)
                cwd = folder / "NumCalc/source_1"
                assert not (cwd / "be.out").exists(), "Template must contain inputs only"
                team_cpus = cpus[slot*args.threads:(slot+1)*args.threads]
                env = environment(args.threads, getattr(args, "malloc_arenas", None))
                handle = (folder / "stdout.log").open("w")
                command = ["taskset", "-c", ",".join(map(str, team_cpus)), str(solver),
                           "-istart", "1", "-iend", "1", "-nitermax", "1000"]
                process = subprocess.Popen(command, cwd=cwd, env=env, stdout=handle,
                                           stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                           start_new_session=True)
                active.append({"process": process, "handle": handle, "folder": folder,
                               "slot": slot, "cpus": team_cpus, "start": time.monotonic(),
                               "peak_rss_gib": 0.0, "id": next_job})
                next_job += 1
            combined_rss = 0.0
            for job in active[:]:
                process = job["process"]
                elapsed = time.monotonic() - job["start"]
                if elapsed > args.timeout:
                    raise RuntimeError("Job timeout")
                try:
                    rss = psutil.Process(process.pid).memory_info().rss / GIB
                    combined_rss += rss
                    job["peak_rss_gib"] = max(job["peak_rss_gib"], rss)
                except psutil.NoSuchProcess:
                    pass
                if process.poll() is None:
                    continue
                job["handle"].close()
                if process.returncode:
                    raise RuntimeError(f"Job {job['id']} exited with {process.returncode}")
                cwd = job["folder"] / "NumCalc/source_1"
                output = (cwd / "NC1-1.out").read_text()
                log = (job["folder"] / "stdout.log").read_text()
                assert "End time:" in output
                cgs = re.findall(CGS, output)
                assert cgs == expected_cgs, ("Iteration/residual mismatch", cgs, expected_cgs)
                hashes = {name: sha(cwd / "be.out/be.1" / name) for name in FIELDS}
                assert hashes == expected, "Numerical field bytes differ"
                observed = re.search(r"MRADM_PERF .* threads (\d+)", log)
                assert observed and int(observed[1]) == args.threads
                regions = {}
                for name, seconds in re.findall(r"MRADM_REGION (\w+) seconds ([0-9.]+)", log):
                    regions[name] = regions.get(name, 0.0) + float(seconds)
                perf = re.search(r"MRADM_PERF calls (\d+) precond_s ([0-9.]+) spmv_s ([0-9.]+)", log)
                result = {"job": job["id"], "wall_seconds": elapsed,
                          "peak_rss_gib": job["peak_rss_gib"], "cpu_affinity": job["cpus"],
                          "iterations": int(cgs[0][0]), "residual": cgs[0][1],
                          "fields_sha256": hashes, "fields_byte_identical": True,
                          "regions_seconds": regions,
                          "matrix_vector_seconds": float(perf[3]),
                          "precondition_seconds": float(perf[2]),
                          "matvec_calls": int(perf[1]),
                          "row_profile": [
                              {"stage": int(stage), "thread": int(thread),
                               "work_seconds": float(seconds), "wait_seconds": float(wait),
                               "samples": int(samples)}
                              for stage, thread, seconds, wait, samples in re.findall(
                                  r"MRADM_ROW stage (\d+) thread (\d+) work_s ([0-9.]+) wait_s ([0-9.]+) samples (\d+)", log)]}
                results.append(result)
                slots.append(job["slot"])
                active.remove(job)
                print("COMPLETE", job["id"], round(elapsed, 3), "seconds", flush=True)
            peak_rss = max(peak_rss, combined_rss)
            now = time.monotonic()
            if now - last_status >= 5:
                save(work / "status.json", {"completed": len(results), "total": count,
                     "elapsed_seconds": now-begin, "memory_gib": used,
                     "running": [{"job": j["id"], "pid": j["process"].pid,
                                  "elapsed_seconds": now-j["start"]} for j in active]})
                last_status = now
            if len(results) < count:
                time.sleep(.2)
        report.update(passed=True, wall_seconds=time.monotonic()-begin,
                      peak_total_memory_gib=peak_total, peak_combined_rss_gib=peak_rss,
                      jobs=sorted(results, key=lambda item: item["job"]))
    except BaseException as error:
        report.update(error=repr(error), jobs=results)
        raise
    finally:
        stop(active)
        save(work / "report.json", report)
        signal.signal(signal.SIGTERM, old_handler)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("solver", "template", "reference-dir", "work-dir"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--pause-control", type=Path)
    parser.add_argument("--processes", type=int, default=1)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--copies", type=int, default=1)
    parser.add_argument("--memory-limit-gib", type=float, default=112)
    parser.add_argument("--expected-rss-gib", type=float, required=True)
    parser.add_argument("--timeout", type=float, default=7200)
    parser.add_argument("--malloc-arenas", type=int, help="Explicit glibc MALLOC_ARENA_MAX for this experiment")
    args = parser.parse_args()
    if min(args.processes, args.threads, args.copies, args.expected_rss_gib, args.timeout) <= 0:
        parser.error("Counts, memory reservation, and timeout must be positive")
    if args.malloc_arenas is not None and args.malloc_arenas <= 0:
        parser.error("--malloc-arenas must be positive")
    print(json.dumps(run_batch(args), indent=2), flush=True)


if __name__ == "__main__":
    main()
