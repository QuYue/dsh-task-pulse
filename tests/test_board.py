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
        self.session = "test-session"
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
            [PY, str(BOARD), "--home", str(self.home), "--root", str(self.root),
             "--session", self.session, *args],
            capture_output=True, text=True,
        )
        if check and result.returncode != 0:
            self.fail(f"board.py {' '.join(args)} failed: {result.stderr}")
        return result

    def init(self, plan_path=None):
        result = self.cli("init", "--plan-file", str(plan_path or self.plan_path))
        return result.stdout

    def status(self):
        return json.loads(self.cli("--json", "status").stdout)

    def session_root(self):
        return self.root / "sessions" / self.session

    def task_ids(self):
        base = self.session_root() / "tasks"
        return sorted(path.name for path in base.iterdir()) if base.exists() else []

    def run_dir(self):
        dirs = list((self.session_root() / "tasks").glob("*/plan.json"))
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

    def post_json(self, path, payload):
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read())

    # -- prune helpers ---------------------------------------------------
    def init_runs(self, *run_ids):
        """Create one run per id; later ids get newer directory mtimes."""
        for run_id in run_ids:
            self.cli("init", "--run", run_id, "--plan-file", str(self.plan_path))
        base = 1_700_000_000
        for index, run_id in enumerate(run_ids, start=1):
            stamp = base + index
            os.utime(self.session_root() / "tasks" / run_id, (stamp, stamp))

    def set_plan_status(self, run_id, status):
        path = self.session_root() / "tasks" / run_id / "plan.json"
        plan = json.loads(path.read_text(encoding="utf-8"))
        plan["status"] = status
        path.write_text(json.dumps(plan), encoding="utf-8")

    def run_ids_on_disk(self):
        return self.task_ids()

    # -- tests -----------------------------------------------------------
    def test_init_registers_project_and_writes_artifacts(self):
        self.init()
        run_dir = self.run_dir()
        self.assertTrue((run_dir / "state.json").exists())
        self.assertTrue((run_dir / "BOARD.md").exists())
        projects = json.loads((self.home / "projects.json").read_text())["projects"]
        self.assertIn(self.session, projects)
        self.assertEqual(projects[self.session]["kind"], "local")
        self.assertEqual(projects[self.session]["sessionId"], self.session)
        view = self.status()
        self.assertTrue(view["title"].endswith("测试任务"))
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

    def test_api_state_allows_cors(self):
        self.init()
        self.start_server()
        with urllib.request.urlopen(
                f"http://127.0.0.1:{self.port}/api/state", timeout=2) as response:
            self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), "*")
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/state", method="OPTIONS")
        with urllib.request.urlopen(request, timeout=2) as response:
            self.assertEqual(response.status, 204)
            self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), "*")

    def test_project_register_api_adds_local_project(self):
        self.init()
        self.start_server()
        other = self.base / "other-project"
        (other / "tasks").mkdir(parents=True)
        payload = {
            "projectId": "other-session",
            "sessionId": "other-session",
            "name": "Other",
            "path": str(other),
        }
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/project/register",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(request, timeout=2) as response:
            self.assertEqual(response.status, 200)
        data = self.wait_state(
            lambda state: "other-session" in [project["id"] for project in state["projects"]])
        self.assertIn("other-session", [project["id"] for project in data["projects"]])

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

    def test_delete_task_api(self):
        self.init()
        self.start_server()
        task_id = self.run_dir().name
        result = self.post_json("/api/task/delete", {
            "projectId": self.session, "taskId": task_id, "confirm": True,
        })
        self.assertTrue(result["ok"])
        self.assertFalse((self.session_root() / "tasks" / task_id).exists())
        self.wait_state(lambda data: any(
            p["id"] == self.session and not p["runs"] for p in data["projects"]))

    def test_delete_project_api_purges_local_session(self):
        self.init()
        self.start_server()
        result = self.post_json("/api/project/delete", {
            "projectId": self.session, "confirm": True, "purge": True,
        })
        self.assertTrue(result["ok"])
        self.assertFalse(self.session_root().exists())
        projects = json.loads((self.home / "projects.json").read_text())["projects"]
        self.assertNotIn(self.session, projects)

    def test_delete_requires_confirm(self):
        self.init()
        self.start_server()
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.post_json("/api/task/delete", {
                "projectId": self.session, "taskId": self.run_dir().name,
            })
        self.assertEqual(caught.exception.code, 400)

    def test_push_sends_local_run_to_hub(self):
        self.init()
        run_dir = self.run_dir()
        self.start_server()
        self.cli("project", "add", "--id", self.session, "--name", "推送",
                 "--kind", "ingest", "--json")
        result = self.cli("push", "--to", f"http://127.0.0.1:{self.port}",
                          "--project-id", self.session, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        pushed = json.loads(result.stdout)
        self.assertGreaterEqual(pushed.get("accepted", 0), 1)
        state = self.wait_state(
            lambda data: any(p["id"] == self.session and p["runs"] for p in data["projects"]))
        project = next(p for p in state["projects"] if p["id"] == self.session)
        self.assertTrue(project["runs"][0]["steps"])


    def test_exec_records_success_and_heartbeats(self):
        self.init()
        log = self.base / "exec-success.log"
        result = self.cli(
            "exec", "s2", "--agent", "coder", "--heartbeat", "0.2", "--quiet",
            "--log", str(log), "--",
            PY, "-c", "import time; print('exec-ok'); time.sleep(0.6)",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        view = self.status()
        step = next(item for item in view["steps"] if item["id"] == "s2")
        self.assertEqual(step["status"], "done")
        self.assertIn(str(log.resolve()), step["evidence"])
        self.assertTrue(log.exists())
        self.assertIn("exec-ok", log.read_text())
        events = (self.run_dir() / "events" / "coder.jsonl").read_text()
        self.assertIn('"heartbeat"', events)

    def test_exec_marks_failed_on_nonzero_exit(self):
        self.init()
        result = self.cli(
            "exec", "s2", "--agent", "coder", "--quiet", "--",
            PY, "-c", "import sys; print('boom'); sys.exit(3)",
            check=False,
        )
        self.assertEqual(result.returncode, 3)
        step = next(item for item in self.status()["steps"] if item["id"] == "s2")
        self.assertEqual(step["status"], "failed")
        self.assertIn("exit 3", step["note"])

    def test_exec_timeout_kills_command(self):
        self.init()
        started = time.time()
        result = self.cli(
            "exec", "s2", "--agent", "coder", "--heartbeat", "0.2",
            "--timeout", "0.5", "--quiet", "--",
            PY, "-c", "import time; time.sleep(30)",
            check=False,
        )
        elapsed = time.time() - started
        self.assertEqual(result.returncode, 124)
        self.assertLess(elapsed, 8)
        step = next(item for item in self.status()["steps"] if item["id"] == "s2")
        self.assertEqual(step["status"], "failed")
        self.assertIn("timeout", step["note"])

    def test_migrate_adopts_legacy_runs(self):
        legacy = self.root / "runs" / "old-task"
        (legacy / "events").mkdir(parents=True)
        plan = dict(BASE_PLAN)
        plan["title"] = "旧任务"
        plan["createdAt"] = "2026-11-02T09:30:00+08:00"
        legacy.joinpath("plan.json").write_text(json.dumps(plan), encoding="utf-8")
        self.cli("migrate", "--session-title", "迁移会话")
        migrated = self.session_root() / "tasks" / "old-task" / "plan.json"
        self.assertTrue(migrated.exists())
        data = json.loads(migrated.read_text())
        self.assertEqual(data["sessionId"], self.session)
        self.assertTrue(data["name"].startswith("09:30 · "))

    def test_init_creates_session_task_with_time_name(self):
        self.init()
        view = self.status()
        self.assertEqual(view["sessionId"], self.session)
        self.assertIn(" · ", view["title"])
        self.assertTrue((self.session_root() / "tasks").exists())

    def test_report_and_heartbeat_progress(self):
        self.init()
        self.cli("start", "s2", "--agent", "coder")
        self.cli("report", "s2", "--percent", "40", "--agent", "coder",
                 "--current", "读取数据")
        self.cli("heartbeat", "--agent", "coder", "--step", "s2",
                 "--percent", "65", "--current", "处理中")
        step = next(item for item in self.status()["steps"] if item["id"] == "s2")
        self.assertEqual(step["progress"], 65)
        self.assertEqual(step["status"], "in_progress")

    def test_exec_exposes_progress_env(self):
        self.init()
        log = self.base / "exec-env.log"
        self.cli("exec", "s2", "--agent", "coder", "--quiet", "--log", str(log), "--",
                 PY, "-c", "import os; print('STEP=' + os.environ['LIVE_PROGRESS_STEP']); "
                          "print('SESSION=' + os.environ['LIVE_PROGRESS_SESSION'])")
        text = log.read_text()
        self.assertIn("STEP=s2", text)
        self.assertIn("SESSION=" + self.session, text)

    def test_exec_keeps_wrapped_command_flags(self):
        self.init()
        log = self.base / "exec-args.log"
        result = self.cli(
            "exec", "s2", "--agent", "coder", "--quiet", "--log", str(log), "--",
            PY, "-c", "import sys; print('ARGS=' + ','.join(sys.argv[1:]))",
            "--json", "--home", "foo",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ARGS=--json,--home,foo", log.read_text())


    # -- prune -----------------------------------------------------------
    def test_prune_dry_run_reports_candidates_without_deleting(self):
        self.init_runs("r1", "r2", "r3")
        self.set_plan_status("r1", "completed")
        self.set_plan_status("r2", "completed")
        result = self.cli("--json", "prune", "--keep", "1", "--dry-run")
        summary = json.loads(result.stdout)
        self.assertEqual(summary["kept"], ["r3"])
        self.assertEqual(sorted(summary["deleted"]), ["r1", "r2"])
        self.assertEqual(summary["skipped"], [])
        self.assertEqual(self.run_ids_on_disk(), ["r1", "r2", "r3"])

    def test_prune_keep_yes_deletes_old_runs(self):
        self.init_runs("r1", "r2", "r3")
        self.set_plan_status("r1", "completed")
        self.set_plan_status("r2", "completed")
        result = self.cli("--json", "prune", "--keep", "1", "--yes")
        summary = json.loads(result.stdout)
        self.assertEqual(summary["kept"], ["r3"])
        self.assertEqual(sorted(summary["deleted"]), ["r1", "r2"])
        self.assertEqual(self.run_ids_on_disk(), ["r3"])
        self.assertTrue((self.session_root() / "tasks" / "r3" / "plan.json").exists())

    def test_prune_skips_running_run(self):
        self.init_runs("r1", "r2", "r3")
        self.set_plan_status("r1", "running")
        self.set_plan_status("r2", "completed")
        result = self.cli("--json", "prune", "--keep", "1", "--yes")
        summary = json.loads(result.stdout)
        self.assertEqual(summary["kept"], ["r3"])
        self.assertEqual(summary["deleted"], ["r2"])
        self.assertEqual(summary["skipped"], ["r1"])
        self.assertEqual(self.run_ids_on_disk(), ["r1", "r3"])
        self.assertTrue((self.session_root() / "tasks" / "r1" / "plan.json").exists())

    # -- revise/plan-change guards --------------------------------------
    def write_plan(self, plan, name="revised.json"):
        path = self.base / name
        path.write_text(json.dumps(plan), encoding="utf-8")
        return path

    def revise_plan(self, plan, check=True):
        path = self.write_plan(plan)
        return self.cli("revise", "--plan-file", str(path), "--reason", "test", "--by", "lead", check=check)

    def plan_copy(self):
        return json.loads(json.dumps(BASE_PLAN))

    def test_revise_removing_already_superseded_step_does_not_duplicate(self):
        self.init()
        plan = self.plan_copy()
        plan["steps"] = [step for step in plan["steps"] if step["id"] != "s3"]
        self.revise_plan(plan)
        self.revise_plan(plan)
        saved = json.loads((self.run_dir() / "plan.json").read_text())
        s3 = [step for step in saved["steps"] if step["id"] == "s3"]
        self.assertEqual(len(s3), 1)
        self.assertTrue(s3[0]["superseded"])

    def test_revise_rejects_reusing_superseded_step_id(self):
        self.init()
        without = self.plan_copy()
        without["steps"] = [step for step in without["steps"] if step["id"] != "s3"]
        self.revise_plan(without)
        result = self.revise_plan(self.plan_copy(), check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("superseded", result.stderr)

    def test_revise_rejects_unknown_dependency(self):
        self.init()
        plan = self.plan_copy()
        plan["steps"][3]["dependsOn"] = ["s9"]
        result = self.revise_plan(plan, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown step", result.stderr)

    def test_revise_rejects_dependency_cycle(self):
        self.init()
        plan = self.plan_copy()
        plan["steps"][0]["dependsOn"] = ["s2"]
        result = self.revise_plan(plan, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cycle", result.stderr)

    def test_revise_reopens_completed_task_when_adding_steps(self):
        self.init()
        for step in ("s1", "s2", "s3", "s4"):
            self.cli("start", step, "--agent", "lead")
            self.cli("done", step, "--agent", "lead")
        self.cli("close", "--by", "lead")
        plan = self.plan_copy()
        plan["steps"].append({
            "id": "s5", "phaseId": "p1", "title": "追加", "owner": "lead",
        })
        self.revise_plan(plan)
        saved = json.loads((self.run_dir() / "plan.json").read_text())
        self.assertEqual(saved["status"], "running")
        self.assertIsNone(saved["completedAt"])
        self.assertIn("s5", [step["id"] for step in saved["steps"]])

    def test_revise_order_controls_display_order(self):
        self.init()
        plan = self.plan_copy()
        plan["steps"][0]["order"] = 30   # s1
        plan["steps"][1]["order"] = 10   # s2
        plan["steps"][2]["order"] = 20   # s3
        plan["steps"][3]["order"] = 40   # s4
        self.revise_plan(plan)
        view = self.status()
        ids = [step["id"] for step in view["steps"]]
        self.assertEqual(ids, ["s2", "s3", "s1", "s4"])

    def test_superseded_step_rejects_further_events(self):
        self.init()
        plan = self.plan_copy()
        plan["steps"] = [step for step in plan["steps"] if step["id"] != "s3"]
        self.revise_plan(plan)
        result = self.cli("start", "s3", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("superseded", result.stderr)

    def test_prune_rejects_keep_zero(self):
        self.init_runs("r1")
        result = self.cli("prune", "--keep", "0", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--keep", result.stderr)
        self.assertEqual(self.run_ids_on_disk(), ["r1"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
