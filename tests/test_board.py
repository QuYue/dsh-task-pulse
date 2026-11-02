"""Black-box tests for live-progress board (stdlib unittest, no third-party deps)."""
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BOARD = REPO / "skill" / "scripts" / "board.py"
PY = sys.executable

BASE_PLAN = {
    "title": "测试任务",
    "goal": "验证 board 行为",
    "phases": [{"id": "p1", "title": "执行"}],
    "agents": [
        {"id": "lead", "name": "lead", "role": "主控"},
        {"id": "coder", "name": "coder", "role": "编程"},
        {"id": "reviewer", "name": "reviewer", "role": "审查"},
    ],
    "steps": [
        {"id": "s1", "phaseId": "p1", "title": "第一步", "owner": "lead"},
        {"id": "s2", "phaseId": "p1", "title": "第二步", "owner": "coder", "dependsOn": ["s1"]},
        {"id": "s3", "phaseId": "p1", "title": "第三步", "owner": "coder", "dependsOn": ["s2"]},
        {"id": "s4", "phaseId": "p1", "title": "审查", "owner": "reviewer", "dependsOn": ["s2"]},
    ],
}


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class BoardTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.home = self.base / "hub"
        self.root = self.base / "proj"
        self.plan_path = self.base / "plan.json"
        self.plan_path.write_text(json.dumps(BASE_PLAN), encoding="utf-8")
        self.server = None
        self.port = None

    def tearDown(self):
        if self.server is not None and self.server.poll() is None:
            self.server.terminate()
            try:
                self.server.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.server.kill()
        self.tmp.cleanup()

    # -- helpers ---------------------------------------------------------
    def cli(self, *args, check=True):
        result = subprocess.run(
            [PY, str(BOARD), "--home", str(self.home), "--root", str(self.root), *args],
            capture_output=True, text=True,
        )
        if check and result.returncode != 0:
            self.fail(f"board.py {' '.join(args)} failed: {result.stderr}")
        return result

    def init(self, project="demo", plan_path=None):
        result = self.cli("init", "--project-id", project,
                          "--plan-file", str(plan_path or self.plan_path))
        return result.stdout

    def status(self):
        return json.loads(self.cli("--json", "status").stdout)

    def run_dir(self):
        dirs = list((self.root / "runs").glob("*/plan.json"))
        self.assertEqual(len(dirs), 1)
        return dirs[0].parent

    def start_server(self):
        self.port = free_port()
        self.server = subprocess.Popen(
            [PY, str(BOARD), "--home", str(self.home), "serve",
             "--port", str(self.port), "--no-notify"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        deadline = time.time() + 8
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(
                        f"http://127.0.0.1:{self.port}/api/health", timeout=0.3) as response:
                    if json.loads(response.read()).get("ok"):
                        return
            except Exception:
                time.sleep(0.05)
        self.fail("server did not start")

    def api_state(self):
        with urllib.request.urlopen(
                f"http://127.0.0.1:{self.port}/api/state", timeout=2) as response:
            return json.loads(response.read())

    def wait_state(self, predicate, timeout=5):
        deadline = time.time() + timeout
        last = None
        while time.time() < deadline:
            last = self.api_state()
            if predicate(last):
                return last
            time.sleep(0.1)
        self.fail(f"timeout waiting for state; last={json.dumps(last)[:600]}")

    def post_ingest(self, payload):
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/ingest",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read())

    # -- tests -----------------------------------------------------------
    def test_init_registers_project_and_writes_artifacts(self):
        self.init()
        run_dir = self.run_dir()
        self.assertTrue((run_dir / "state.json").exists())
        self.assertTrue((run_dir / "BOARD.md").exists())
        projects = json.loads((self.home / "projects.json").read_text())["projects"]
        self.assertIn("demo", projects)
        self.assertEqual(projects["demo"]["kind"], "local")
        view = self.status()
        self.assertEqual(view["title"], "测试任务")
        self.assertEqual(view["revision"], 1)
        self.assertEqual(len(view["steps"]), 4)
        self.assertEqual(view["progress"]["percent"], 0)

    def test_lifecycle_and_chain(self):
        self.init()
        self.cli("start", "s1", "--agent", "lead")
        self.cli("done", "s1", "--agent", "lead", "--evidence", "notes/a.md",
                 "--start", "s2", "--next-agent", "coder")
        view = self.status()
        steps = {step["id"]: step for step in view["steps"]}
        self.assertEqual(steps["s1"]["status"], "done")
        self.assertEqual(steps["s1"]["evidence"], ["notes/a.md"])
        self.assertEqual(steps["s2"]["status"], "in_progress")
        self.assertEqual(view["progress"]["percent"], 25)

    def test_parallel_progress_and_blocked_by(self):
        self.init()
        self.cli("start", "s2", "--agent", "coder")
        self.cli("start", "s4", "--agent", "reviewer")
        view = self.status()
        steps = {step["id"]: step for step in view["steps"]}
        self.assertEqual(view["progress"]["inProgress"], 2)
        self.assertEqual(steps["s3"]["status"], "pending")
        self.assertEqual(steps["s3"]["blockedBy"], ["s2"])

    def test_revise_marks_removed_step_superseded(self):
        self.init()
        mutated = json.loads(json.dumps(BASE_PLAN))
        mutated["title"] = "测试任务 v2"
        mutated["steps"] = [step for step in mutated["steps"] if step["id"] != "s4"]
        mutated["steps"].append({"id": "s5", "phaseId": "p1", "title": "新增步骤", "owner": "coder"})
        mutated["reason"] = "范围变更"
        new_plan = self.base / "plan-v2.json"
        new_plan.write_text(json.dumps(mutated), encoding="utf-8")
        self.cli("revise", "--plan-file", str(new_plan), "--reason", "范围变更", "--by", "lead")
        view = self.status()
        self.assertEqual(view["revision"], 2)
        steps = {step["id"]: step for step in view["steps"]}
        self.assertEqual(steps["s4"]["status"], "superseded")
        self.assertEqual(steps["s5"]["status"], "pending")
        change = view["changes"][0]
        self.assertEqual(change["rev"], 2)
        self.assertIn("s5", change["added"])
        self.assertIn("s4", change["removed"])

    def test_close_requires_terminal_steps(self):
        self.init()
        failed = self.cli("close", "--by", "lead", check=False)
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn("s1", failed.stderr)
        self.cli("close", "--by", "lead", "--force")
        self.assertEqual(self.status()["status"], "completed")

    def test_heartbeat_updates_agent_and_current_text(self):
        self.init()
        self.cli("start", "s2", "--agent", "coder")
        self.cli("heartbeat", "--agent", "coder", "--step", "s2", "--current", "写代码中")
        view = self.status()
        agent = next(item for item in view["agents"] if item["id"] == "coder")
        self.assertEqual(agent["status"], "working")
        self.assertEqual(agent["currentStep"], "s2")
        self.assertEqual(agent["currentText"], "写代码中")
        self.assertIsNotNone(agent["lastSeenAgoSec"])

    def test_unknown_step_fails(self):
        self.init()
        result = self.cli("start", "nope", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown step", result.stderr)

    def test_render_all(self):
        self.init()
        self.cli("render", "--all")
        self.assertTrue((self.run_dir() / "BOARD.md").exists())

    def test_ingest_is_idempotent_and_token_protected(self):
        self.init()
        self.start_server()
        out = self.cli("project", "add", "--id", "remote", "--name", "远程",
                       "--kind", "ingest", "--json")
        token = json.loads(out.stdout)["token"]
        payload = {
            "project": {"id": "remote", "name": "远程"},
            "run": {"id": "r1", "title": "远程任务", "goal": "g", "revision": 1, "status": "running"},
            "plan": {
                "title": "远程任务",
                "phases": [{"id": "p1", "title": "阶段"}],
                "agents": [{"id": "srv", "role": "主控"}],
                "steps": [{"id": "x1", "phaseId": "p1", "title": "远程步骤", "owner": "srv"}],
            },
            "events": [{"uuid": "u1", "agent": "srv", "type": "start", "stepId": "x1"}],
            "token": token,
        }
        first = self.post_ingest(payload)
        self.assertEqual(first["accepted"], 1)
        second = self.post_ingest(payload)
        self.assertEqual(second["accepted"], 0)
        self.assertEqual(second["duplicate"], 1)
        state = self.wait_state(
            lambda data: any(p["id"] == "remote" for p in data["projects"]))
        project = next(p for p in state["projects"] if p["id"] == "remote")
        self.assertEqual(project["kind"], "ingest")
        self.assertEqual(project["runs"][0]["steps"][0]["status"], "in_progress")

        bad = dict(payload)
        bad["token"] = "wrong"
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.post_ingest(bad)
        self.assertEqual(caught.exception.code, 403)

    def test_push_sends_local_run_to_hub(self):
        self.init(project="pushme")
        run_dir = self.run_dir()
        self.start_server()
        self.cli("project", "add", "--id", "pushme", "--name", "推送",
                 "--kind", "ingest", "--json")
        result = self.cli("push", "--to", f"http://127.0.0.1:{self.port}",
                          "--project-id", "pushme", check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        pushed = json.loads(result.stdout)
        self.assertGreaterEqual(pushed.get("accepted", 0), 1)
        state = self.wait_state(
            lambda data: any(p["id"] == "pushme" and p["runs"] for p in data["projects"]))
        project = next(p for p in state["projects"] if p["id"] == "pushme")
        self.assertTrue(project["runs"][0]["steps"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
