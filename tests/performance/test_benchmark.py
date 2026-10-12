"""Resource and production-state guards; no solver jobs are launched."""
import io
import json
from pathlib import Path
import signal
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import benchmark


class BenchmarkGuards(unittest.TestCase):
    def test_allocator_override_is_child_local(self):
        with patch.dict(benchmark.os.environ, {"MALLOC_ARENA_MAX": "2"}):
            self.assertEqual(benchmark.environment(8)["MALLOC_ARENA_MAX"], "2")
            self.assertEqual(benchmark.environment(32, 32)["MALLOC_ARENA_MAX"], "32")
            self.assertEqual(benchmark.os.environ["MALLOC_ARENA_MAX"], "2")

    def args(self, root, **changes):
        values = dict(work_dir=root / "run", solver=root / "NumCalc",
                      processes=1, threads=8, copies=1, pause_control=None,
                      expected_rss_gib=25, memory_limit_gib=112,
                      template=root / "template", reference_dir=root / "reference",
                      timeout=7200)
        values.update(changes)
        return SimpleNamespace(**values)

    @patch.object(benchmark.subprocess, "Popen")
    @patch.object(benchmark.os, "sched_getaffinity", return_value=set(range(32)), create=True)
    def test_memory_reservation_prevents_launch(self, affinity, launch):
        with tempfile.TemporaryDirectory() as temp, patch.object(benchmark, "memory_gib", return_value=12):
            args = self.args(Path(temp), processes=4)
            with self.assertRaisesRegex(ValueError, "headroom"):
                benchmark.run_batch(args)
        launch.assert_not_called()

    @patch.object(benchmark.subprocess, "Popen")
    @patch.object(benchmark.os, "sched_getaffinity", return_value=set(range(8)), create=True)
    def test_cpu_oversubscription_prevents_launch(self, affinity, launch):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "CPU"):
                benchmark.run_batch(self.args(Path(temp), processes=2))
        launch.assert_not_called()

    @patch.object(benchmark.subprocess, "Popen")
    @patch.object(benchmark.os, "sched_getaffinity", return_value=set(range(32)), create=True)
    def test_live_production_dispatch_prevents_launch(self, affinity, launch):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            control = root / "control.json"
            control.write_text(json.dumps({"allow_fullband": True}))
            with self.assertRaisesRegex(ValueError, "paused"):
                benchmark.run_batch(self.args(root, pause_control=control))
        launch.assert_not_called()

    def test_cleanup_targets_only_owned_live_processes(self):
        live, done = Mock(pid=111), Mock(pid=222)
        live.poll.return_value = None
        done.poll.return_value = 0
        handles = [io.StringIO(), io.StringIO()]
        jobs = [{"process": live, "handle": handles[0]}, {"process": done, "handle": handles[1]}]
        with patch.object(benchmark.os, "killpg", side_effect=ProcessLookupError) as kill:
            benchmark.stop(jobs)
        kill.assert_called_once_with(111, signal.SIGTERM)
        self.assertTrue(all(handle.closed for handle in handles))
        live.wait.assert_called_once()
        done.wait.assert_called_once()


if __name__ == "__main__":
    unittest.main()
