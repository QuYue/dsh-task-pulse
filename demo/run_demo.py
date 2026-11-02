#!/usr/bin/env python3
"""live-progress demo.

Two projects at once:
  * demo-wordcount (local): lead + coder + reviewer + a background test job run in
    parallel, a plan revision happens mid-run, then the run is closed.
  * demo-remote (ingest): events are POSTed to /api/ingest as if they came from a
    server, showing the token-protected remote path.

The script starts the hub if it is not already running on the port, then leaves it
running by default so the page can be inspected afterwards (Ctrl+C stops it).

Usage:
    python3 demo/run_demo.py [--open] [--fast] [--speed 1.0]
"""
from __future__ import annotations

import argparse
import json
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
import webbrowser
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BOARD = REPO / "skill" / "scripts" / "board.py"
DEMO_DIR = Path(__file__).resolve().parent
DEMO_A = DEMO_DIR / "demo_a"
PROGRESS_A = DEMO_A / ".dsh" / "progress"
ARTIFACTS = DEMO_A / "artifacts"
HOME = DEMO_DIR / ".hub"
PORT = 8770

PROJECT_LOCAL = "demo-wordcount"
PROJECT_REMOTE = "demo-remote"


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
        result = http_json(f"http://127.0.0.1:{port}/api/health", timeout=0.8)
        return bool(result.get("ok"))
    except Exception:
        return False


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


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


def board_cli(*args, home: Path, root: Path | None = None):
    command = [sys.executable, str(BOARD), "--home", str(home)]
    if root is not None:
        command += ["--root", str(root)]
    command += list(args)
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"board.py {' '.join(args)} failed:\n{result.stderr}")
    return result.stdout.strip()


def plan_v1() -> dict:
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


def plan_v2() -> dict:
    plan = plan_v1()
    plan["title"] = "wordcount 增加 JSON/CSV 输出"
    plan["goal"] = "支持 --json 与 --csv，补齐测试，全量测试通过"
    plan["steps"].append({
        "id": "s6", "phaseId": "p2", "title": "实现 --csv 参数", "owner": "coder",
        "size": "M", "acceptance": "输出合法 CSV", "dependsOn": ["s2"],
    })
    plan["reason"] = "用户追加 CSV 导出需求"
    return plan


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
            {"id": "r1", "phaseId": "p1", "title": "备份预检", "owner": "server-lead",
             "size": "S", "acceptance": "备份可用"},
            {"id": "r2", "phaseId": "p2", "title": "迁移 dry-run", "owner": "server-coder",
             "size": "L", "acceptance": "无报错、行数一致", "dependsOn": ["r1"]},
            {"id": "r3", "phaseId": "p3", "title": "审查校验脚本", "owner": "server-reviewer",
             "size": "M", "acceptance": "覆盖空表/重复键", "dependsOn": ["r1"]},
            {"id": "r4", "phaseId": "p3", "title": "正式执行", "owner": "server-lead",
             "size": "L", "acceptance": "对账一致", "dependsOn": ["r2", "r3"]},
        ],
    }


def scenario_local(args, home: Path, port: int) -> None:
    root = PROGRESS_A
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    plan_file = home / "plan-v1.json"
    plan_file.write_text(json.dumps(plan_v1(), ensure_ascii=False, indent=2), encoding="utf-8")
    out = board_cli("init", "--project-id", PROJECT_LOCAL, "--name", "Demo · wordcount 重构",
                    "--plan-file", str(plan_file), home=home, root=root)
    print(f"[local] {out.splitlines()[0] if out else 'initialized'}")

    pause(1.0, args.speed)
    board_cli("start", "s1", "--agent", "lead", home=home, root=root)
    print("[local] lead 开始 s1 读代码")
    pause(1.6, args.speed)
    (ARTIFACTS / "wordcount-notes.md").write_text(
        "# 调研笔记\n- 现有 CLI 只输出总数\n- 需要新增 --json / --csv\n", encoding="utf-8")
    board_cli("heartbeat", "--agent", "lead", "--step", "s1", "--current", "整理改动点",
              home=home, root=root)
    pause(1.6, args.speed)
    board_cli("done", "s1", "--agent", "lead", "--evidence", "artifacts/wordcount-notes.md",
              "--note", "改动点已整理", home=home, root=root)
    print("[local] s1 完成")

    board_cli("start", "s2", "--agent", "coder", home=home, root=root)
    print("[local] coder 开始 s2 实现 --json")
    pause(2.2, args.speed)
    (ARTIFACTS / "wordcount_json.py").write_text(
        "#!/usr/bin/env python3\n# demo artifact: --json implementation\n", encoding="utf-8")
    board_cli("heartbeat", "--agent", "coder", "--step", "s2", "--current", "实现 --json 序列化",
              home=home, root=root)
    plan_file_v2 = home / "plan-v2.json"
    plan_file_v2.write_text(json.dumps(plan_v2(), ensure_ascii=False, indent=2), encoding="utf-8")
    pause(1.0, args.speed)
    board_cli("revise", "--plan-file", str(plan_file_v2), "--reason", "用户追加 CSV 导出需求",
              "--by", "lead", home=home, root=root)
    print("[local] 计划升到 v2：新增 s6（CSV）")
    pause(1.8, args.speed)
    board_cli("done", "s2", "--agent", "coder", "--evidence", "artifacts/wordcount_json.py",
              "--note", "json 输出与帮助已加", home=home, root=root)
    print("[local] s2 完成")

    board_cli("start", "s3", "--agent", "coder", home=home, root=root)
    board_cli("start", "s4", "--agent", "reviewer", home=home, root=root)
    print("[local] 并行：coder s3 补测试 / reviewer s4 审查")
    pause(1.3, args.speed)
    board_cli("heartbeat", "--agent", "coder", "--step", "s3", "--current", "写 test_json 用例",
              home=home, root=root)
    board_cli("heartbeat", "--agent", "reviewer", "--step", "s4", "--current", "检查边界条件",
              home=home, root=root)
    pause(1.6, args.speed)
    (ARTIFACTS / "test_json.py").write_text("# demo artifact: json tests\n", encoding="utf-8")
    board_cli("heartbeat", "--agent", "coder", "--step", "s3", "--current", "跑新用例",
              home=home, root=root)
    board_cli("heartbeat", "--agent", "reviewer", "--step", "s4", "--current", "写审查结论",
              home=home, root=root)
    pause(1.2, args.speed)
    (ARTIFACTS / "review.md").write_text("# 审查结论\n无阻塞性问题。\n", encoding="utf-8")
    board_cli("done", "s4", "--agent", "reviewer", "--evidence", "artifacts/review.md",
              "--note", "无阻塞性问题", home=home, root=root)
    print("[local] s4 审查完成")
    pause(0.6, args.speed)
    board_cli("done", "s3", "--agent", "coder", "--evidence", "artifacts/test_json.py",
              "--note", "3 个用例通过", home=home, root=root)
    print("[local] s3 测试完成")

    board_cli("start", "s5", "--agent", "bg-1", home=home, root=root)
    board_cli("start", "s6", "--agent", "coder", home=home, root=root)
    print("[local] 并行：后台 job s5 跑测试 / coder s6 实现 --csv")
    pause(1.4, args.speed)
    board_cli("heartbeat", "--agent", "bg-1", "--step", "s5", "--current", "pytest 运行中",
              home=home, root=root)
    board_cli("heartbeat", "--agent", "coder", "--step", "s6", "--current", "实现 --csv",
              home=home, root=root)
    pause(1.6, args.speed)
    (ARTIFACTS / "test.log").write_text("5 passed in 0.21s\n", encoding="utf-8")
    board_cli("heartbeat", "--agent", "bg-1", "--step", "s5", "--current", "pytest 运行中",
              home=home, root=root)
    pause(1.4, args.speed)
    board_cli("done", "s5", "--agent", "bg-1", "--evidence", "artifacts/test.log",
              "--note", "5 passed", home=home, root=root)
    print("[local] s5 全量测试通过")
    pause(0.5, args.speed)
    board_cli("done", "s6", "--agent", "coder", "--note", "CSV 输出完成",
              home=home, root=root)
    print("[local] s6 完成")
    pause(1.0, args.speed)
    board_cli("close", "--by", "lead", home=home, root=root)
    print("[local] 运行已关闭")


def scenario_remote(args, home: Path, port: int) -> None:
    base = f"http://127.0.0.1:{port}"
    out = board_cli("project", "add", "--id", PROJECT_REMOTE,
                    "--name", "Demo · 远程订单迁移", "--kind", "ingest", "--json",
                    home=home)
    token = json.loads(out)["token"]
    plan = remote_plan()
    run_id = "remote-" + time.strftime("%Y%m%d-%H%M%S")

    def events(*items):
        return [dict(item, uuid=uuid.uuid4().hex, ts=None) for item in items]

    def push(events_list, status="running", plan_payload=None):
        payload = {
            "project": {"id": PROJECT_REMOTE, "name": "Demo · 远程订单迁移", "color": "#a06bff"},
            "run": {"id": run_id, "title": plan["title"], "goal": plan["goal"],
                    "revision": 1, "status": status},
            "plan": plan_payload,
            "events": [{key: value for key, value in event.items() if value is not None}
                       for event in events_list],
            "token": token,
        }
        return http_json(base + "/api/ingest", payload)

    push([], "running", plan)
    print("[remote] 推送计划 v1 到本地 hub")
    pause(1.2, args.speed)
    push([{"agent": "server-lead", "type": "start", "stepId": "r1"}])
    pause(1.4, args.speed)
    push([{"agent": "server-lead", "type": "done", "stepId": "r1",
           "note": "备份校验通过", "evidence": ["/srv/reports/backup-check.txt"]}])
    print("[remote] r1 备份预检完成")
    pause(0.8, args.speed)
    push([{"agent": "server-coder", "type": "start", "stepId": "r2"},
          {"agent": "server-reviewer", "type": "start", "stepId": "r3"}])
    print("[remote] 并行：server-coder r2 / server-reviewer r3")
    for _ in range(2):
        pause(1.2, args.speed)
        push([{"agent": "server-coder", "type": "heartbeat", "stepId": "r2",
               "current": "执行 dry-run 迁移"},
              {"agent": "server-reviewer", "type": "heartbeat", "stepId": "r3",
               "current": "审查校验脚本"}])
    pause(1.2, args.speed)
    push([{"agent": "server-coder", "type": "done", "stepId": "r2",
           "note": "dry-run 无报错", "evidence": ["/srv/reports/dryrun.log"]}])
    pause(0.8, args.speed)
    push([{"agent": "server-reviewer", "type": "done", "stepId": "r3",
           "note": "覆盖空表/重复键"}])
    pause(0.8, args.speed)
    push([{"agent": "server-lead", "type": "start", "stepId": "r4"}], )
    pause(1.4, args.speed)
    push([{"agent": "server-lead", "type": "done", "stepId": "r4",
           "note": "对账一致"}], status="completed")
    print("[remote] 远程 run 已完成")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="live-progress demo")
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--open", action="store_true", help="open the board in a browser")
    parser.add_argument("--fast", action="store_true", help="3x speed")
    parser.add_argument("--speed", type=float, default=1.0, help="time scale (2 = slower)")
    parser.add_argument("--no-keep-server", action="store_true",
                        help="stop the hub this script started when the demo ends")
    parser.add_argument("--fresh", action="store_true", help="remove previous demo data first")
    parser.add_argument("--local-only", action="store_true")
    parser.add_argument("--remote-only", action="store_true")
    args = parser.parse_args(argv)
    if args.fast:
        args.speed = max(args.speed, 3.0)
    home = HOME
    home.mkdir(parents=True, exist_ok=True)
    if args.fresh:
        shutil.rmtree(PROGRESS_A, ignore_errors=True)
        shutil.rmtree(home / "inbox" / PROJECT_REMOTE, ignore_errors=True)

    port = args.port
    server = None
    log = None
    started_here = False
    if hub_health(port):
        print(f"[hub] 复用已运行的看板 http://127.0.0.1:{port}/")
    else:
        if args.port == PORT:
            pass
        server, log = start_hub(port, home)
        started_here = True
        print(f"[hub] 已启动看板 http://127.0.0.1:{port}/")

    try:
        remote_thread = None
        if not args.local_only:
            remote_thread = threading.Thread(
                target=scenario_remote, args=(args, home, port), daemon=True)
            remote_thread.start()
        if not args.remote_only:
            scenario_local(args, home, port)
        if remote_thread is not None:
            remote_thread.join()
        print("")
        print(f"看板: http://127.0.0.1:{port}/")
        print(f"本地数据: {PROGRESS_A}")
        print(f"远程镜像: {home / 'inbox' / PROJECT_REMOTE}")
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
