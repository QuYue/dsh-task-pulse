#!/usr/bin/env python3
"""live-progress demo (v3 model: project = session, task = request).

Two DSH sessions are simulated:
  * demo-session        — two tasks in the same session (wordcount JSON/CSV, fix README)
  * demo-remote-session — one task pushed from a "server" via /api/ingest

The hub is started if it is not already running. By default it is left running so
the pages can be inspected afterwards (Ctrl+C stops it).

Usage:
    python3 demo/run_demo.py [--open] [--fast] [--speed 1.0] [--fresh]
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import uuid
import webbrowser
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BOARD = REPO / "skill" / "scripts" / "board.py"
DEMO_DIR = Path(__file__).resolve().parent
DEMO_A = DEMO_DIR / "demo_a"
PROGRESS_ROOT = DEMO_A / ".dsh" / "progress"
ARTIFACTS = DEMO_A / "artifacts"
HOME = DEMO_DIR / ".hub"
PORT = 8770

LOCAL_SESSION = "demo-session"
LOCAL_TITLE = "Demo 会话 · 本地任务"
REMOTE_SESSION = "demo-remote-session"
REMOTE_TITLE = "Demo 会话 · 远程任务"


def pause(seconds: float, speed: float) -> None:
    time.sleep(max(0.0, seconds / speed))


def http_json(url: str, payload=None, timeout: float = 10.0):
    data = None
    headers = {}
    method = "GET"
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
        method = "POST"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
        return json.loads(body) if body else {}


def hub_health(port: int) -> bool:
    try:
        return bool(http_json(f"http://127.0.0.1:{port}/api/health", timeout=0.8).get("ok"))
    except Exception:
        return False


def start_hub(port: int, home: Path):
    home.mkdir(parents=True, exist_ok=True)
    log = open(home / "hub-server.log", "a", encoding="utf-8")
    process = subprocess.Popen(
        [sys.executable, str(BOARD), "--home", str(home), "serve", "--port", str(port)],
        cwd=str(REPO), stdout=log, stderr=log,
    )
    for _ in range(100):
        if hub_health(port):
            return process, log
        if process.poll() is not None:
            log.close()
            raise SystemExit(f"hub exited early; see {home / 'hub-server.log'}")
        time.sleep(0.1)
    process.terminate()
    log.close()
    raise SystemExit("hub did not become healthy in time")


def run_board(*args, session=LOCAL_SESSION, json_out=False):
    command = [sys.executable, str(BOARD), "--home", str(HOME),
               "--root", str(PROGRESS_ROOT), "--session", session]
    if json_out:
        command.append("--json")
    command += list(args)
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"board.py {' '.join(args)} failed:\n{result.stderr}\n{result.stdout}")
    return result.stdout.strip()


def init_task(plan: dict, session: str, title: str) -> dict:
    path = HOME / f"plan-{session}-{int(time.time() * 1000)}.json"
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    out = run_board("init", "--plan-file", str(path), "--session-title", title,
                    session=session, json_out=True)
    return json.loads(out)


def plan_wordcount() -> dict:
    return {
        "title": "wordcount 增加 JSON 输出",
        "goal": "支持 --json 并补齐测试，全量测试通过",
        "phases": [
            {"id": "p1", "title": "调研"},
            {"id": "p2", "title": "实现"},
            {"id": "p3", "title": "验证"},
        ],
        "agents": [
            {"id": "lead", "name": "lead", "role": "主控", "kind": "lead"},
            {"id": "coder", "name": "coder", "role": "编程", "kind": "teammate"},
            {"id": "reviewer", "name": "reviewer", "role": "审查", "kind": "teammate"},
            {"id": "bg-1", "name": "bg-1", "role": "后台任务", "kind": "job"},
        ],
        "steps": [
            {"id": "s1", "phaseId": "p1", "title": "读现有代码与测试", "owner": "lead",
             "size": "S", "acceptance": "列出改动点"},
            {"id": "s2", "phaseId": "p2", "title": "实现 --json 参数", "owner": "coder",
             "size": "M", "acceptance": "CLI 输出合法 JSON", "dependsOn": ["s1"]},
            {"id": "s3", "phaseId": "p2", "title": "补 JSON 输出测试", "owner": "coder",
             "size": "M", "acceptance": "新增用例全绿", "dependsOn": ["s2"]},
            {"id": "s4", "phaseId": "p2", "title": "审查实现", "owner": "reviewer",
             "size": "S", "acceptance": "无阻塞性问题", "dependsOn": ["s2"]},
            {"id": "s5", "phaseId": "p3", "title": "跑全量测试", "owner": "bg-1",
             "size": "S", "acceptance": "测试全绿", "dependsOn": ["s2", "s3"]},
        ],
    }


def plan_wordcount_v2() -> dict:
    plan = plan_wordcount()
    plan["title"] = "wordcount 增加 JSON/CSV 输出"
    plan["goal"] = "支持 --json 与 --csv，补齐测试，全量测试通过"
    plan["steps"].append({
        "id": "s6", "phaseId": "p2", "title": "实现 --csv 参数", "owner": "coder",
        "size": "M", "acceptance": "输出合法 CSV", "dependsOn": ["s2"],
    })
    plan["reason"] = "用户追加 CSV 导出需求"
    return plan


def plan_readme() -> dict:
    return {
        "title": "修复 README 拼写",
        "goal": "修正 README 中的错别字与失效链接",
        "phases": [{"id": "p1", "title": "修复"}],
        "agents": [{"id": "lead", "name": "lead", "role": "主控", "kind": "lead"}],
        "steps": [
            {"id": "r1", "phaseId": "p1", "title": "检查错别字", "owner": "lead", "size": "S"},
            {"id": "r2", "phaseId": "p1", "title": "修复并校对", "owner": "lead", "size": "S",
             "dependsOn": ["r1"]},
        ],
    }


def scenario_local(args) -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    task_a = init_task(plan_wordcount(), LOCAL_SESSION, LOCAL_TITLE)
    print(f"[local] task A: {task_a['name']} ({task_a['taskId']})")

    run_board("start", "s1", "--agent", "lead")
    pause(1.2, args.speed)
    (ARTIFACTS / "wordcount-notes.md").write_text("# 调研笔记\n- 现有 CLI 只输出总数\n", encoding="utf-8")
    run_board("done", "s1", "--agent", "lead", "--evidence", "artifacts/wordcount-notes.md",
              "--note", "改动点已整理")
    print("[local] s1 完成")

    run_board("start", "s2", "--agent", "coder")
    pause(1.0, args.speed)
    run_board("report", "s2", "--percent", "45", "--agent", "coder", "--current", "实现 --json 序列化")
    run_board("heartbeat", "--agent", "coder", "--step", "s2", "--percent", "45",
              "--current", "正在写 JSON 分支")
    pause(1.2, args.speed)
    plan_v2 = HOME / f"plan-v2-{int(time.time() * 1000)}.json"
    plan_v2.write_text(json.dumps(plan_wordcount_v2(), ensure_ascii=False, indent=2), encoding="utf-8")
    run_board("revise", "--plan-file", str(plan_v2), "--reason", "用户追加 CSV 导出需求", "--by", "lead")
    run_board("report", "s2", "--percent", "80", "--agent", "coder", "--current", "补帮助文本")
    pause(0.8, args.speed)
    (ARTIFACTS / "wordcount_json.py").write_text("# artifact: json implementation\n", encoding="utf-8")
    run_board("done", "s2", "--agent", "coder", "--evidence", "artifacts/wordcount_json.py",
              "--note", "json 输出完成")
    print("[local] s2 完成，计划升到 v2（新增 s6）")

    run_board("start", "s3", "--agent", "coder")
    run_board("start", "s4", "--agent", "reviewer")
    pause(0.8, args.speed)
    run_board("report", "s3", "--percent", "30", "--agent", "coder", "--current", "写 test_json 用例")
    run_board("report", "s4", "--percent", "35", "--agent", "reviewer", "--current", "检查边界条件")
    pause(1.0, args.speed)
    run_board("report", "s3", "--percent", "70", "--agent", "coder", "--current", "跑新用例")
    run_board("report", "s4", "--percent", "75", "--agent", "reviewer", "--current", "写审查结论")
    pause(0.8, args.speed)
    (ARTIFACTS / "review.md").write_text("# 审查结论\n无阻塞性问题。\n", encoding="utf-8")
    run_board("done", "s4", "--agent", "reviewer", "--evidence", "artifacts/review.md",
              "--note", "无阻塞性问题")
    (ARTIFACTS / "test_json.py").write_text("# artifact: json tests\n", encoding="utf-8")
    run_board("done", "s3", "--agent", "coder", "--evidence", "artifacts/test_json.py",
              "--note", "3 个用例通过")
    print("[local] s3/s4 并行完成")

    command = (
        "import time;"
        "print('progress: 20'); time.sleep(1.0);"
        "print('progress: 60'); time.sleep(1.0);"
        "print('progress: 90'); time.sleep(0.3);"
        "print('tests passed')"
    )
    run_board("exec", "s5", "--agent", "bg-1", "--heartbeat", "1", "--quiet", "--",
              sys.executable, "-c", command)
    print("[local] s5 后台测试完成（exec 自动记账）")

    run_board("start", "s6", "--agent", "coder")
    pause(0.6, args.speed)
    run_board("report", "s6", "--percent", "50", "--agent", "coder", "--current", "实现 --csv")
    pause(0.6, args.speed)
    run_board("done", "s6", "--agent", "coder", "--note", "CSV 输出完成")
    print("[local] s6 完成")
    pause(0.8, args.speed)
    run_board("close", "--by", "lead")

    task_b = init_task(plan_readme(), LOCAL_SESSION, LOCAL_TITLE)
    print(f"[local] task B: {task_b['name']} ({task_b['taskId']})")
    run_board("start", "r1", "--agent", "lead")
    pause(0.7, args.speed)
    run_board("done", "r1", "--agent", "lead", "--note", "发现 2 处拼写问题")
    run_board("start", "r2", "--agent", "lead")
    pause(0.7, args.speed)
    run_board("done", "r2", "--agent", "lead", "--note", "已修复并校对")
    run_board("close", "--by", "lead")
    print("[local] task B 完成")


def remote_plan() -> dict:
    return {
        "title": "订单库迁移 dry-run",
        "goal": "完成 dry-run 并产出校验报告",
        "phases": [
            {"id": "p1", "title": "预检"},
            {"id": "p2", "title": "迁移"},
            {"id": "p3", "title": "验证"},
        ],
        "agents": [
            {"id": "server-lead", "name": "server-lead", "role": "主控", "kind": "lead"},
            {"id": "server-coder", "name": "server-coder", "role": "编程", "kind": "teammate"},
            {"id": "server-reviewer", "name": "server-reviewer", "role": "审查", "kind": "teammate"},
        ],
        "steps": [
            {"id": "r1", "phaseId": "p1", "title": "备份预检", "owner": "server-lead", "size": "S"},
            {"id": "r2", "phaseId": "p2", "title": "迁移 dry-run", "owner": "server-coder", "size": "L",
             "dependsOn": ["r1"]},
            {"id": "r3", "phaseId": "p3", "title": "审查校验脚本", "owner": "server-reviewer", "size": "M",
             "dependsOn": ["r1"]},
            {"id": "r4", "phaseId": "p3", "title": "正式执行", "owner": "server-lead", "size": "L",
             "dependsOn": ["r2", "r3"]},
        ],
    }


def scenario_remote(args, port: int) -> None:
    out = run_board("project", "add", "--id", REMOTE_SESSION, "--name", REMOTE_TITLE,
                    "--kind", "ingest", "--json", session=REMOTE_SESSION, json_out=True)
    token = json.loads(out)["token"]
    base = f"http://127.0.0.1:{port}"
    plan = remote_plan()
    run_id = "remote-" + time.strftime("%Y%m%d-%H%M%S")
    started_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    def push(events=None, status="running"):
        payload = {
            "project": {"id": REMOTE_SESSION, "name": REMOTE_TITLE},
            "task": {
                "id": run_id, "title": plan["title"], "goal": plan["goal"],
                "revision": 1, "status": status, "startedAt": started_at,
            },
            "events": events or [],
            "token": token,
        }
        if not events:
            payload["plan"] = plan
        return http_json(base + "/api/ingest", payload)

    push()
    print("[remote] 推送计划到本地 hub")
    pause(1.0, args.speed)
    push([{"uuid": uuid.uuid4().hex, "agent": "server-lead", "type": "start", "stepId": "r1"}])
    pause(1.2, args.speed)
    push([{"uuid": uuid.uuid4().hex, "agent": "server-lead", "type": "done", "stepId": "r1",
           "note": "备份校验通过", "evidence": ["/srv/reports/backup-check.txt"]}])
    pause(0.8, args.speed)
    push([
        {"uuid": uuid.uuid4().hex, "agent": "server-coder", "type": "start", "stepId": "r2"},
        {"uuid": uuid.uuid4().hex, "agent": "server-reviewer", "type": "start", "stepId": "r3"},
    ])
    pause(1.2, args.speed)
    push([
        {"uuid": uuid.uuid4().hex, "agent": "server-coder", "type": "report", "stepId": "r2",
         "progress": 40, "current": "执行 dry-run 迁移"},
        {"uuid": uuid.uuid4().hex, "agent": "server-reviewer", "type": "report", "stepId": "r3",
         "progress": 55, "current": "审查校验脚本"},
    ])
    pause(1.2, args.speed)
    push([{"uuid": uuid.uuid4().hex, "agent": "server-coder", "type": "done", "stepId": "r2",
           "note": "dry-run 无报错", "evidence": ["/srv/reports/dryrun.log"]}])
    pause(0.8, args.speed)
    push([{"uuid": uuid.uuid4().hex, "agent": "server-reviewer", "type": "done", "stepId": "r3",
           "note": "覆盖空表/重复键"}])
    pause(0.8, args.speed)
    push([{"uuid": uuid.uuid4().hex, "agent": "server-lead", "type": "start", "stepId": "r4"}])
    pause(1.0, args.speed)
    push([{"uuid": uuid.uuid4().hex, "agent": "server-lead", "type": "done", "stepId": "r4",
           "note": "对账一致"}], status="completed")
    print("[remote] 远程任务完成")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="live-progress demo")
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--open", action="store_true")
    parser.add_argument("--fast", action="store_true")
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--no-keep-server", action="store_true")
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument("--local-only", action="store_true")
    parser.add_argument("--remote-only", action="store_true")
    args = parser.parse_args(argv)
    if args.fast:
        args.speed = max(args.speed, 3.0)
    HOME.mkdir(parents=True, exist_ok=True)
    if args.fresh:
        shutil.rmtree(PROGRESS_ROOT / "sessions" / LOCAL_SESSION, ignore_errors=True)
        shutil.rmtree(HOME / "inbox" / REMOTE_SESSION, ignore_errors=True)

    port = args.port
    server = None
    log = None
    started_here = False
    if hub_health(port):
        print(f"[hub] 复用已运行的看板 http://127.0.0.1:{port}/")
    else:
        server, log = start_hub(port, HOME)
        started_here = True
        print(f"[hub] 已启动看板 http://127.0.0.1:{port}/")

    try:
        remote_thread = None
        if not args.local_only:
            remote_thread = threading.Thread(
                target=scenario_remote, args=(args, port), daemon=True)
            remote_thread.start()
        if not args.remote_only:
            scenario_local(args)
        if remote_thread is not None:
            remote_thread.join()
        print("")
        print(f"看板: http://127.0.0.1:{port}/")
        print(f"本地会话: http://127.0.0.1:{port}/p/{LOCAL_SESSION}")
        print(f"远程会话: http://127.0.0.1:{port}/p/{REMOTE_SESSION}")
        if args.open:
            webbrowser.open(f"http://127.0.0.1:{port}/")
        if started_here and not args.no_keep_server:
            print("看板服务保持运行中（Ctrl+C 结束）…")
            while True:
                time.sleep(0.5)
        return 0
    except KeyboardInterrupt:
        print("\n停止…")
        return 0
    finally:
        if started_here and (args.no_keep_server or server is None or server.poll() is not None):
            if server is not None and server.poll() is None:
                server.terminate()
                try:
                    server.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    server.kill()
        if log is not None:
            log.close()


if __name__ == "__main__":
    raise SystemExit(main())
