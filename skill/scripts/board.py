#!/usr/bin/env python3
"""live-progress board v1 — file-first real-time task progress for DSH agents.

Design: files are the single source of truth. Agents append events; the Lead owns the
versioned plan; the hub server is a read-only viewer plus a token-protected ingest
endpoint for remote runs. See docs/contract.md for the full interface.

Only Python stdlib is used.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import random
import re
import signal
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from contextlib import contextmanager
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from queue import Empty, Queue
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

try:  # POSIX only; the skill targets macOS/Linux
    import fcntl
except Exception:  # pragma: no cover
    fcntl = None

VERSION = "1.0"
SCHEMA = 1
DEFAULT_PORT = 8770
DEFAULT_HOST = "127.0.0.1"
STALE_SEC = 180          # UI warning threshold for a working agent
NOTIFY_STALE_SEC = 300   # notify once when a working agent is silent this long
PRESENCE_TTL = 30        # seconds a browser tab counts as open
RUN_SUFFIX = uuid.uuid4().hex[:4]
TERMINAL_STEPS = {"done", "failed", "skipped", "superseded"}
OPEN_STEPS = {"pending", "in_progress", "blocked"}
STATUS_ZH = {
    "pending": "待开始", "in_progress": "进行中", "blocked": "阻塞",
    "done": "完成", "failed": "失败", "skipped": "跳过", "superseded": "已取消",
    "working": "干活中", "idle": "空闲", "running": "运行中", "completed": "已完成",
}
TYPE_TO_STATUS = {
    "start": "in_progress", "resume": "in_progress", "done": "done",
    "block": "blocked", "fail": "failed", "skip": "skipped",
}
PALETTE = ["#4f8cff", "#3ddc97", "#ffb454", "#c792ea", "#ff6b81",
           "#39c5cf", "#e6c07b", "#8892a6", "#8fb4ff", "#5ec8a0"]


# --------------------------------------------------------------------------- utils

def now_dt() -> datetime:
    return datetime.now().astimezone()


def iso(dt: datetime | None = None) -> str:
    return (dt or now_dt()).isoformat(timespec="seconds")


def parse_ts(value):
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        return dt if dt.tzinfo else dt.astimezone()
    except Exception:
        return None


def ts_key(value) -> float:
    dt = parse_ts(value)
    return dt.timestamp() if dt else 0.0


def ago_sec(value, now: datetime | None = None):
    dt = parse_ts(value)
    if not dt:
        return None
    return max(0, int((now or now_dt()).timestamp() - dt.timestamp()))


def slugify(value, fallback="item") -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value or "")).strip("-._")
    return text or f"{fallback}-{uuid.uuid4().hex[:6]}"


def fmt_duration(ms) -> str:
    if ms is None:
        return "—"
    sec = max(0, int(ms // 1000))
    if sec < 60:
        return f"{sec}s"
    if sec < 3600:
        return f"{sec // 60}m{sec % 60:02d}s"
    return f"{sec // 3600}h{(sec % 3600) // 60:02d}m"


def fmt_ago(sec) -> str:
    if sec is None:
        return "—"
    if sec < 60:
        return f"{sec}s 前"
    if sec < 3600:
        return f"{sec // 60}m 前"
    return f"{sec // 3600}h 前"


def hash_color(seed: str) -> str:
    digest = hashlib.md5(seed.encode("utf-8")).hexdigest()
    return PALETTE[int(digest[:8], 16) % len(PALETTE)]


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp." + uuid.uuid4().hex[:6])
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_json(path: Path, obj) -> None:
    atomic_write_text(path, json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def read_json(path: Path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


@contextmanager
def file_lock(lock_path: Path, timeout: float = 8.0):
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(lock_path, "a+")
    locked = False
    try:
        if fcntl is not None:
            deadline = time.time() + timeout
            while True:
                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    locked = True
                    break
                except (BlockingIOError, OSError):
                    if time.time() > deadline:
                        raise TimeoutError(f"lock timeout: {lock_path}")
                    time.sleep(0.02)
        yield
    finally:
        if locked and fcntl is not None:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
        handle.close()


# --------------------------------------------------------------------- locations

def default_home() -> Path:
    env = os.environ.get("DSH_PROGRESS_HOME")
    if env:
        return Path(env).expanduser()
    preferred = Path.home() / ".dsh" / "progress"
    try:
        preferred.mkdir(parents=True, exist_ok=True)
        return preferred
    except OSError:
        # sandboxed session (workspace-write): keep the hub inside the workspace
        return Path.cwd() / ".dsh" / "progress" / "hub"


def resolve_home(args) -> Path:
    return Path(args.home).expanduser().resolve() if getattr(args, "home", None) else default_home()


def resolve_root(args) -> Path:
    if getattr(args, "root", None):
        return Path(args.root).expanduser().resolve()
    return (Path.cwd() / ".dsh" / "progress").resolve()


def runs_path(root: Path) -> Path:
    return Path(root) / "runs"


def run_dirs(root: Path):
    base = runs_path(root)
    if not base.exists():
        return []
    found = [p for p in base.iterdir() if p.is_dir() and (p / "plan.json").exists()]
    found.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return found


def resolve_run(root: Path, run_id: str | None = None) -> Path | None:
    if run_id:
        candidate = runs_path(root) / slugify(run_id, "run")
        return candidate if (candidate / "plan.json").exists() else None
    dirs = run_dirs(root)
    return dirs[0] if dirs else None


def project_base(home: Path, project: dict) -> Path:
    if project.get("kind") == "ingest":
        return Path(home) / "inbox" / project["id"]
    return Path((project.get("source") or {}).get("path") or "")


# ----------------------------------------------------------------------- registry

def projects_file(home: Path) -> Path:
    return Path(home) / "projects.json"


def load_projects(home: Path) -> dict:
    data = read_json(projects_file(home), None)
    if not isinstance(data, dict):
        data = {}
    data.setdefault("version", 1)
    data.setdefault("projects", {})
    return data


def _save_projects_locked(home: Path, data: dict) -> None:
    write_json(projects_file(home), data)


def register_project(home: Path, project_id: str, name: str | None = None,
                     color: str | None = None, kind: str = "local",
                     path: str | None = None, token: str | None = None) -> dict:
    project_id = slugify(project_id, "project")
    home = Path(home)
    with file_lock(home / ".projects.lock"):
        data = load_projects(home)
        entry = data["projects"].get(project_id) or {}
        entry.setdefault("id", project_id)
        entry.setdefault("createdAt", iso())
        if name:
            entry["name"] = name
        entry.setdefault("name", project_id)
        if color:
            entry["color"] = color
        entry.setdefault("color", hash_color(project_id))
        entry["kind"] = kind
        source = entry.get("source") or {}
        if path:
            source["path"] = str(Path(path).expanduser().resolve())
        if kind == "ingest":
            entry["token"] = token or entry.get("token") or uuid.uuid4().hex
        entry["source"] = source
        data["projects"][project_id] = entry
        _save_projects_locked(home, data)
        return dict(entry)


def unregister_project(home: Path, project_id: str, purge: bool = False) -> bool:
    home = Path(home)
    with file_lock(home / ".projects.lock"):
        data = load_projects(home)
        entry = data["projects"].pop(project_id, None)
        if entry is None:
            return False
        _save_projects_locked(home, data)
    if purge and entry.get("kind") == "ingest":
        purge_dir = home / "inbox" / project_id
        if purge_dir.exists():
            import shutil
            shutil.rmtree(purge_dir, ignore_errors=True)
    return True


def list_projects(home: Path) -> list:
    data = load_projects(home)
    return sorted(data["projects"].values(), key=lambda p: p.get("name", p["id"]))


# --------------------------------------------------------------------------- plan

def default_kind(agent_id: str) -> str:
    if agent_id == "lead":
        return "lead"
    if agent_id.startswith("bg-") or agent_id.startswith("job-"):
        return "job"
    return "teammate"


def default_role(agent_id: str) -> str:
    return {
        "lead": "主控", "coder": "编程", "reviewer": "审查", "tester": "测试",
        "planner": "规划", "bg": "后台任务",
    }.get(agent_id, "后台任务" if default_kind(agent_id) == "job" else "执行")


def make_agent(agent_id: str, data: dict | None = None) -> dict:
    data = data or {}
    return {
        "id": agent_id,
        "name": str(data.get("name") or agent_id),
        "role": str(data.get("role") or default_role(agent_id)),
        "color": str(data.get("color") or hash_color(agent_id)),
        "kind": str(data.get("kind") or default_kind(agent_id)),
    }


def normalize_plan(raw: dict, run_id: str) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("plan must be a JSON object")
    plan = dict(raw)
    title = str(plan.get("title") or "").strip()
    if not title:
        raise ValueError("plan.title is required")

    phases = []
    phase_ids = set()
    for index, phase in enumerate(plan.get("phases") or []):
        phase = phase or {}
        phase_id = slugify(phase.get("id") or f"p{index + 1}", "p")
        if phase_id in phase_ids:
            raise ValueError(f"duplicate phase id: {phase_id}")
        phase_ids.add(phase_id)
        phases.append({"id": phase_id, "title": str(phase.get("title") or phase_id)})
    if not phases:
        phases = [{"id": "p1", "title": "执行"}]
        phase_ids = {"p1"}

    steps = []
    step_ids = set()
    for index, step in enumerate(plan.get("steps") or []):
        step = step or {}
        step_id = slugify(step.get("id") or f"s{index + 1}", "s")
        if step_id in step_ids:
            raise ValueError(f"duplicate step id: {step_id}")
        step_ids.add(step_id)
        phase_id = slugify(step.get("phaseId") or phases[0]["id"], "p")
        if phase_id not in phase_ids:
            phases.append({"id": phase_id, "title": phase_id})
            phase_ids.add(phase_id)
        steps.append({
            "id": step_id,
            "phaseId": phase_id,
            "title": str(step.get("title") or step_id),
            "owner": str(step.get("owner") or "lead"),
            "size": str(step.get("size") or "M"),
            "acceptance": str(step.get("acceptance") or ""),
            "dependsOn": [slugify(dep, "s") for dep in (step.get("dependsOn") or [])],
            "note": str(step.get("note") or ""),
            "superseded": bool(step.get("superseded")),
        })
    if not steps:
        raise ValueError("plan.steps must contain at least one step")

    agents = {}
    for agent in plan.get("agents") or []:
        if not agent:
            continue
        agent_id = slugify(agent.get("id") or "", "")
        if agent_id:
            agents[agent_id] = make_agent(agent_id, agent)
    for step in steps:
        owner = step["owner"]
        agents.setdefault(owner, make_agent(owner))

    return {
        "title": title,
        "goal": str(plan.get("goal") or ""),
        "runId": run_id,
        "revision": max(1, int(plan.get("revision") or 1)),
        "status": str(plan.get("status") or "running"),
        "createdAt": plan.get("createdAt") or iso(),
        "updatedAt": plan.get("updatedAt") or iso(),
        "completedAt": plan.get("completedAt"),
        "agents": list(agents.values()),
        "phases": phases,
        "steps": steps,
        "changes": list(plan.get("changes") or []),
    }


def load_plan(run_dir: Path) -> dict | None:
    return read_json(Path(run_dir) / "plan.json")


def save_plan(run_dir: Path, plan: dict) -> None:
    with file_lock(Path(run_dir) / ".plan.lock"):
        write_json(Path(run_dir) / "plan.json", plan)


# ------------------------------------------------------------------------- events

def append_event(run_dir: Path, event: dict) -> dict:
    event = dict(event)
    event.setdefault("uuid", uuid.uuid4().hex)
    event.setdefault("ts", iso())
    agent = slugify(event.get("agent") or "lead", "agent")
    event["agent"] = agent
    if event.get("type") is None:
        raise ValueError("event.type is required")
    events_dir = Path(run_dir) / "events"
    events_dir.mkdir(parents=True, exist_ok=True)
    line = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
    with open(events_dir / f"{agent}.jsonl", "a", encoding="utf-8") as handle:
        handle.write(line + "\n")
        handle.flush()
        try:
            os.fsync(handle.fileno())
        except OSError:
            pass
    return event


def read_events(run_dir: Path) -> list:
    """Read all agent logs. Within one agent file, append order wins; across agents
    we order by timestamp (same-second ties fall back to agent file name)."""
    collected = []
    events_dir = Path(run_dir) / "events"
    if not events_dir.exists():
        return []
    for path in sorted(events_dir.glob("*.jsonl")):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line_no, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except Exception:
                continue
            if not isinstance(event, dict):
                continue
            event.setdefault("uuid", uuid.uuid4().hex)
            event.setdefault("agent", path.stem)
            collected.append((ts_key(event.get("ts")), path.stem, line_no, event))
    collected.sort(key=lambda item: (item[0], item[1], item[2]))
    return [item[3] for item in collected]


# -------------------------------------------------------------------- derive view

def _event_evidence(event: dict) -> list:
    raw = event.get("evidence")
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, (list, tuple)):
        return [str(item) for item in raw if item]
    return []


def _step_states(events: list) -> dict:
    states = {}
    for event in events:
        step_id = event.get("stepId")
        event_type = event.get("type")
        if not step_id or event_type not in TYPE_TO_STATUS:
            continue
        record = states.setdefault(step_id, {
            "status": "pending", "startedAt": None, "endedAt": None,
            "note": "", "evidence": [], "blockedReason": "",
        })
        record["status"] = TYPE_TO_STATUS[event_type]
        if event_type in ("start", "resume"):
            record["startedAt"] = event.get("ts")
            record["endedAt"] = None
        elif event_type in ("done", "fail", "skip", "block"):
            record["endedAt"] = event.get("ts")
        if event_type == "block":
            record["blockedReason"] = str(event.get("note") or event.get("reason") or "")
        if event.get("note"):
            record["note"] = str(event.get("note"))
        evidence = _event_evidence(event)
        if evidence:
            record["evidence"] = evidence
    return states


def build_run_view(run_dir: Path, now: datetime | None = None) -> dict | None:
    now = now or now_dt()
    plan = load_plan(run_dir)
    if not plan:
        return None
    events = read_events(run_dir)
    states = _step_states(events)

    plan_steps = plan.get("steps") or []
    step_ids = {step["id"] for step in plan_steps}
    step_views = []
    by_id = {}
    for step in plan_steps:
        record = states.get(step["id"], {})
        superseded = bool(step.get("superseded"))
        status = "superseded" if superseded else record.get("status", "pending")
        started_at = record.get("startedAt")
        ended_at = record.get("endedAt")
        elapsed = None
        if started_at:
            start_dt = parse_ts(started_at)
            end_dt = parse_ts(ended_at) if ended_at else now
            if start_dt and end_dt:
                elapsed = max(0, int((end_dt - start_dt).total_seconds() * 1000))
        blocked_by = []
        if status in OPEN_STEPS:
            for dep in step.get("dependsOn") or []:
                if dep not in step_ids:
                    blocked_by.append(dep)
                    continue
                dep_state = states.get(dep, {})
                dep_status = "superseded" if _is_superseded(plan_steps, dep) else dep_state.get("status", "pending")
                if dep_status not in TERMINAL_STEPS:
                    blocked_by.append(dep)
        view = {
            "id": step["id"],
            "phaseId": step["phaseId"],
            "title": step["title"],
            "owner": step["owner"],
            "status": status,
            "size": step.get("size", "M"),
            "acceptance": step.get("acceptance", ""),
            "startedAt": started_at,
            "endedAt": ended_at,
            "elapsedMs": elapsed,
            "blockedBy": blocked_by,
            "note": record.get("note") or step.get("note") or "",
            "evidence": record.get("evidence") or [],
            "jobId": step.get("jobId"),
        }
        step_views.append(view)
        by_id[view["id"]] = view

    accounted = {"skipped", "superseded"}
    total = sum(1 for view in step_views if view["status"] not in accounted)
    done = sum(1 for view in step_views if view["status"] == "done")
    in_progress = sum(1 for view in step_views if view["status"] == "in_progress")
    failed = sum(1 for view in step_views if view["status"] == "failed")
    skipped = sum(1 for view in step_views if view["status"] == "skipped")
    percent = int(round(done / total * 100)) if total else 0

    phases = []
    for phase in plan.get("phases") or []:
        phase_steps = [view for view in step_views if view["phaseId"] == phase["id"]]
        phase_total = sum(1 for view in phase_steps if view["status"] not in accounted)
        phase_done = sum(1 for view in phase_steps if view["status"] == "done")
        if phase_steps and all(view["status"] in TERMINAL_STEPS for view in phase_steps):
            phase_status = "done"
        elif any(view["status"] in ("in_progress", "blocked", "failed") for view in phase_steps):
            phase_status = "in_progress"
        elif phase_done:
            phase_status = "in_progress"
        else:
            phase_status = "pending"
        phases.append({
            "id": phase["id"],
            "title": phase["title"],
            "status": phase_status,
            "stepIds": [view["id"] for view in phase_steps],
            "done": phase_done,
            "total": phase_total,
        })

    declared = {agent["id"]: make_agent(agent["id"], agent) for agent in plan.get("agents") or []}
    for event in events:
        agent_id = event.get("agent")
        if agent_id and agent_id not in declared:
            declared[agent_id] = make_agent(agent_id)
    agents = []
    for agent_id, agent in declared.items():
        owned = [view for view in step_views if view["owner"] == agent_id]
        active = [view for view in owned if view["status"] == "in_progress"]
        blocked = [view for view in owned if view["status"] == "blocked"]
        agent_events = [event for event in events if event.get("agent") == agent_id]
        last_event = agent_events[-1] if agent_events else None
        last_seen = last_event.get("ts") if last_event else None
        last_ago = ago_sec(last_seen, now)
        current = active[0] if active else (blocked[0] if blocked else None)
        current_text = None
        if last_event and last_event.get("current"):
            current_text = str(last_event.get("current"))
        elif current:
            current_text = current["title"]
        if active:
            status = "working"
        elif blocked:
            status = "blocked"
        elif last_ago is not None and last_ago < 120 and last_event and last_event.get("type") == "heartbeat":
            status = "working"
        else:
            status = "idle"
        stalled = bool(status == "working" and last_ago is not None and last_ago > STALE_SEC)
        agents.append({
            **agent,
            "status": status,
            "currentStep": current["id"] if current else None,
            "currentText": current_text,
            "startedAt": current["startedAt"] if current else None,
            "lastSeen": last_seen,
            "lastSeenAgoSec": last_ago,
            "stalled": stalled,
        })
    agents.sort(key=lambda a: (0 if a["kind"] == "lead" else 1, a["id"]))

    event_views = []
    for event in reversed(events[-60:]):
        item = {
            "uuid": event.get("uuid"),
            "ts": event.get("ts"),
            "agent": event.get("agent"),
            "type": event.get("type"),
            "stepId": event.get("stepId"),
            "note": str(event.get("note") or event.get("reason") or ""),
        }
        if event.get("current"):
            item["current"] = str(event.get("current"))
        evidence = _event_evidence(event)
        if evidence:
            item["evidence"] = evidence
        event_views.append(item)

    changes = list(plan.get("changes") or [])
    changes.reverse()
    updated_at = plan.get("updatedAt") or plan.get("createdAt") or iso(now)
    if events:
        last_ts = max((event.get("ts") for event in events if event.get("ts")), key=ts_key, default=None)
        if last_ts and ts_key(last_ts) > ts_key(updated_at):
            updated_at = last_ts

    return {
        "id": plan.get("runId") or run_dir.name,
        "projectId": plan.get("projectId") or "",
        "title": plan.get("title", ""),
        "goal": plan.get("goal", ""),
        "status": plan.get("status", "running"),
        "revision": int(plan.get("revision") or 1),
        "startedAt": plan.get("createdAt"),
        "updatedAt": updated_at,
        "completedAt": plan.get("completedAt"),
        "progress": {
            "done": done, "total": total, "inProgress": in_progress,
            "failed": failed, "skipped": skipped, "percent": percent,
        },
        "agents": agents,
        "phases": phases,
        "steps": step_views,
        "events": event_views,
        "changes": changes,
        "urls": {
            "page": f"/r/{plan.get('projectId') or ''}/{plan.get('runId') or run_dir.name}",
            "boardMd": str(run_dir / "BOARD.md"),
        },
        "dir": str(run_dir),
    }


def _is_superseded(plan_steps: list, step_id: str) -> bool:
    for step in plan_steps:
        if step.get("id") == step_id:
            return bool(step.get("superseded"))
    return False


def build_global_state(home: Path, now: datetime | None = None) -> dict:
    now = now or now_dt()
    projects = []
    for project in list_projects(home):
        base = project_base(home, project)
        runs = []
        status = "ok"
        if not base.exists():
            status = "missing"
        else:
            for run_dir in run_dirs(base)[:10]:
                view = build_run_view(run_dir, now)
                if view:
                    runs.append(view)
        runs.sort(key=lambda run: ts_key(run.get("updatedAt")), reverse=True)
        last_activity = max((run.get("updatedAt") for run in runs if run.get("updatedAt")),
                            key=ts_key, default=None)
        projects.append({
            "id": project["id"],
            "name": project.get("name") or project["id"],
            "color": project.get("color") or hash_color(project["id"]),
            "kind": project.get("kind", "local"),
            "sourceStatus": status,
            "lastActivityAt": last_activity,
            "runs": runs,
        })
    projects.sort(key=lambda p: ts_key(p.get("lastActivityAt")), reverse=True)
    return {"generatedAt": iso(now), "version": VERSION, "projects": projects}


# ---------------------------------------------------------------------- rendering

def render_markdown(view: dict) -> str:
    def cell(value) -> str:
        return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")

    lines = [f"# {view['title']}", ""]
    if view.get("goal"):
        lines += [f"**目标**：{view['goal']}", ""]
    progress = view["progress"]
    lines += [
        f"- 运行：`{view['id']}`",
        f"- 状态：{STATUS_ZH.get(view['status'], view['status'])}（计划 v{view['revision']}）",
        f"- 进度：{progress['done']}/{progress['total']}（{progress['percent']}%），并行 {progress['inProgress']}",
        f"- 开始：{view.get('startedAt') or '—'}　更新：{view.get('updatedAt') or '—'}",
        "",
        "## 代理",
        "",
        "| 代理 | 角色 | 状态 | 当前步骤 | 最后事件 |",
        "|---|---|---|---|---|",
    ]
    for agent in view["agents"]:
        lines.append("| {name} | {role} | {status} | {current} | {seen} |".format(
            name=cell(agent["name"]), role=cell(agent["role"]),
            status=cell(STATUS_ZH.get(agent["status"], agent["status"])),
            current=cell(agent.get("currentText") or "—"),
            seen=cell(fmt_ago(agent.get("lastSeenAgoSec"))),
        ))
    lines += ["", "## 步骤", "", "| 阶段 | ID | 步骤 | 负责人 | 状态 | 耗时 | 证据 |",
              "|---|---|---|---|---|---|---|"]
    phases = {phase["id"]: phase["title"] for phase in view["phases"]}
    for step in view["steps"]:
        lines.append("| {phase} | {sid} | {title} | {owner} | {status} | {elapsed} | {evidence} |".format(
            phase=cell(phases.get(step["phaseId"], step["phaseId"])),
            sid=cell(step["id"]), title=cell(step["title"]),
            owner=cell(step["owner"]),
            status=cell(STATUS_ZH.get(step["status"], step["status"])),
            elapsed=cell(fmt_duration(step.get("elapsedMs"))),
            evidence=cell(", ".join(step.get("evidence") or []) or "—"),
        ))
    if view.get("changes"):
        lines += ["", "## 计划变更", ""]
        for change in view["changes"]:
            bits = []
            if change.get("added"):
                bits.append("新增 " + ", ".join(change["added"]))
            if change.get("removed"):
                bits.append("取消 " + ", ".join(change["removed"]))
            if change.get("changed"):
                bits.append("修改 " + ", ".join(change["changed"]))
            lines.append(f"- v{change.get('rev')} · {change.get('at')} · {change.get('reason')}" +
                         (f"（{'；'.join(bits)}）" if bits else ""))
    if view.get("events"):
        lines += ["", "## 最近事件", ""]
        for event in view["events"][:20]:
            step = f"[{event['stepId']}] " if event.get("stepId") else ""
            note = f" — {event['note']}" if event.get("note") else ""
            lines.append(f"- {event.get('ts')} · {event.get('agent')} · {event.get('type')} "
                         f"{step}{note}")
    lines.append("")
    return "\n".join(lines)


def render_run(run_dir: Path) -> dict | None:
    view = build_run_view(run_dir)
    if not view:
        return None
    write_json(Path(run_dir) / "state.json", {
        "generatedAt": iso(), "version": VERSION, "run": view,
    })
    atomic_write_text(Path(run_dir) / "BOARD.md", render_markdown(view))
    return view


def maybe_render(run_dir: Path, args) -> None:
    if not getattr(args, "no_render", False):
        render_run(run_dir)


# ------------------------------------------------------------------- notifications

def appscript_quote(text: str) -> str:
    return '"' + str(text).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")[:240] + '"'


def send_desktop_notification(title: str, body: str) -> None:
    try:
        if sys.platform == "darwin":
            script = f"display notification {appscript_quote(body)} with title {appscript_quote(title)}"
            subprocess.run(["osascript", "-e", script], capture_output=True, timeout=6)
        elif sys.platform.startswith("linux"):
            subprocess.run(["notify-send", title, body], capture_output=True, timeout=6)
        elif sys.platform.startswith("win"):
            pass
    except Exception:
        pass


# ------------------------------------------------------------------------- server

class Hub:
    def __init__(self, home: Path, template: Path, notify: bool = True):
        self.home = Path(home)
        self.template = Path(template)
        self.notify = notify
        self.clients: list[Queue] = []
        self.presence: dict[str, float] = {}
        self.lock = threading.Lock()
        self.state_text = ""
        self.snapshot = None
        self.prev_snapshot = None
        self.version = None
        self.stop = threading.Event()
        self.ntfy = threading.Lock()

    # -- lifecycle ---------------------------------------------------------
    def start(self) -> None:
        self.version = self._version()
        self.snapshot = build_global_state(self.home)
        self.prev_snapshot = self.snapshot
        self.state_text = self._dump(self.snapshot)
        thread = threading.Thread(target=self._loop, name="hub-watch", daemon=True)
        thread.start()

    def shutdown(self) -> None:
        self.stop.set()

    def _dump(self, snapshot) -> str:
        return json.dumps(snapshot, ensure_ascii=False, separators=(",", ":"))

    def _runs(self, base: Path) -> list:
        return run_dirs(base)[:10]

    def _version(self):
        items = []
        try:
            items.append(("projects", projects_file(self.home).stat().st_mtime_ns))
        except OSError:
            items.append(("projects", 0))
        try:
            data = load_projects(self.home)
        except Exception:
            data = {"projects": {}}
        for project in data.get("projects", {}).values():
            base = project_base(self.home, project)
            try:
                if not base.exists():
                    items.append((project["id"], "missing"))
                    continue
            except Exception:
                continue
            for run_dir in self._runs(base):
                plan_file = run_dir / "plan.json"
                try:
                    items.append((str(plan_file), plan_file.stat().st_mtime_ns))
                except OSError:
                    pass
                events_dir = run_dir / "events"
                if events_dir.exists():
                    for path in sorted(events_dir.glob("*.jsonl")):
                        try:
                            items.append((str(path), path.stat().st_mtime_ns))
                        except OSError:
                            pass
        return tuple(items)

    def _loop(self) -> None:
        while not self.stop.is_set():
            try:
                version = self._version()
                if version != self.version:
                    self.version = version
                    snapshot = build_global_state(self.home)
                    text = self._dump(snapshot)
                    changed = text != self.state_text
                    self.snapshot = snapshot
                    self.state_text = text
                    if changed:
                        self.broadcast("state", text)
                        self._notify_diff(snapshot)
                        self.prev_snapshot = snapshot
            except Exception as exc:  # keep the watcher alive
                self._log(f"watch error: {exc}")
            time.sleep(0.6)

    def _log(self, message: str) -> None:
        try:
            with open(self.home / "hub.log", "a", encoding="utf-8") as handle:
                handle.write(f"{iso()} {message}\n")
        except Exception:
            pass

    # -- clients -----------------------------------------------------------
    def register_client(self) -> Queue:
        queue: Queue = Queue(maxsize=64)
        with self.lock:
            self.clients.append(queue)
        return queue

    def unregister_client(self, queue: Queue) -> None:
        with self.lock:
            if queue in self.clients:
                self.clients.remove(queue)

    def broadcast(self, event: str, data: str) -> None:
        with self.lock:
            clients = list(self.clients)
        for queue in clients:
            try:
                queue.put_nowait((event, data))
            except Exception:
                pass

    def touch_presence(self, client_id: str) -> None:
        with self.lock:
            self.presence[client_id] = time.time()
            self._prune_presence_locked()

    def _prune_presence_locked(self) -> None:
        cutoff = time.time() - PRESENCE_TTL
        for key in [k for k, t in self.presence.items() if t < cutoff]:
            self.presence.pop(key, None)

    def has_presence(self) -> bool:
        with self.lock:
            self._prune_presence_locked()
            return bool(self.presence)

    # -- notifications -----------------------------------------------------
    def _notify_diff(self, snapshot: dict) -> None:
        previous = self.prev_snapshot
        if not previous:
            return
        old = {(p["id"], r["id"]): r for p in previous.get("projects", []) for r in p.get("runs", [])}
        for project in snapshot.get("projects", []):
            for run in project.get("runs", []):
                key = (project["id"], run["id"])
                old_run = old.get(key)
                if not old_run:
                    continue
                base = {
                    "projectId": project["id"], "runId": run["id"],
                    "url": run.get("urls", {}).get("page", "/"),
                    "createdAt": iso(),
                }
                if old_run.get("status") == "running" and run.get("status") == "completed":
                    self._emit({
                        **base, "kind": "run_completed", "level": "info",
                        "title": f"{project['name']} · 任务完成",
                        "body": run.get("title", ""),
                    })
                if int(run.get("revision") or 1) > int(old_run.get("revision") or 1):
                    latest = (run.get("changes") or [{}])[0]
                    self._emit({
                        **base, "kind": "plan_revise", "level": "warn",
                        "title": f"{project['name']} · 计划升到 v{run['revision']}",
                        "body": latest.get("reason", ""),
                    })
                old_steps = {step["id"]: step for step in old_run.get("steps", [])}
                for step in run.get("steps", []):
                    old_step = old_steps.get(step["id"])
                    if not old_step:
                        continue
                    if old_step.get("status") != step["status"]:
                        if step["status"] == "failed":
                            self._emit({
                                **base, "kind": "step_failed", "level": "error",
                                "title": f"{project['name']} · {step['id']} 失败",
                                "body": step.get("note") or step.get("title", ""),
                            })
                        elif step["status"] == "blocked":
                            self._emit({
                                **base, "kind": "step_blocked", "level": "warn",
                                "title": f"{project['name']} · {step['id']} 阻塞",
                                "body": step.get("note") or step.get("title", ""),
                            })
                old_agents = {agent["id"]: agent for agent in old_run.get("agents", [])}
                for agent in run.get("agents", []):
                    old_agent = old_agents.get(agent["id"])
                    if old_agent and not old_agent.get("stalled") and agent.get("stalled"):
                        if (agent.get("lastSeenAgoSec") or 0) > NOTIFY_STALE_SEC:
                            self._emit({
                                **base, "kind": "stalled", "level": "warn",
                                "title": f"{project['name']} · {agent['name']} 可能停滞",
                                "body": f"{(agent.get('lastSeenAgoSec') or 0) // 60} 分钟无事件",
                            })

    def _emit(self, payload: dict) -> None:
        payload = dict(payload)
        payload["id"] = payload.get("id") or uuid.uuid4().hex
        self.broadcast("notification", self._dump(payload))
        if self.notify and not self.has_presence():
            self._log(f"notify {payload['kind']}: {payload['title']}")
            threading.Thread(
                target=send_desktop_notification,
                args=(payload["title"], payload.get("body", "")),
                daemon=True,
            ).start()

    # -- ingest ------------------------------------------------------------
    def ingest(self, payload: dict):
        project_payload = payload.get("project") or {}
        run_payload = payload.get("run") or {}
        project_id = slugify(project_payload.get("id") or "", "")
        if not project_id:
            return 400, {"ok": False, "error": "project.id is required"}
        data = load_projects(self.home)
        project = data.get("projects", {}).get(project_id)
        token = str(payload.get("token") or "")
        auth = str(payload.get("authorization") or "")
        if auth.startswith("Bearer "):
            token = auth[7:].strip()
        if project is None:
            return 404, {"ok": False, "error": f"unknown project: {project_id}"}
        if project.get("kind") != "ingest":
            return 409, {"ok": False, "error": "project is not an ingest project"}
        if not token or not hmac.compare_digest(token, str(project.get("token") or "")):
            return 403, {"ok": False, "error": "invalid token"}
        run_id = slugify(run_payload.get("id") or "", "")
        if not run_id:
            return 400, {"ok": False, "error": "run.id is required"}
        run_dir = self.home / "inbox" / project_id / "runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "events").mkdir(parents=True, exist_ok=True)
        with file_lock(self.home / ".ingest.lock"):
            existing = load_plan(run_dir)
            plan_payload = payload.get("plan")
            if plan_payload:
                normalized = normalize_plan(plan_payload, run_id)
                incoming_rev = int(run_payload.get("revision") or normalized["revision"] or 1)
                existing_rev = int((existing or {}).get("revision") or 0)
                if existing_rev and incoming_rev < existing_rev:
                    pass  # ignore stale plan revision
                else:
                    normalized.update({
                        "projectId": project_id,
                        "revision": max(incoming_rev, existing_rev if existing else 1),
                        "status": str(run_payload.get("status") or normalized.get("status") or "running"),
                        "createdAt": (existing or {}).get("createdAt") or normalized.get("createdAt") or iso(),
                        "updatedAt": iso(),
                        "completedAt": (existing or {}).get("completedAt"),
                        "changes": plan_payload.get("changes") or (existing or {}).get("changes") or [],
                    })
                    write_json(run_dir / "plan.json", normalized)
            elif existing is None:
                return 400, {"ok": False, "error": "plan is required on first ingest"}

            if run_payload.get("status"):
                current = load_plan(run_dir) or {}
                current["status"] = str(run_payload["status"])
                current["updatedAt"] = iso()
                if current["status"] == "completed":
                    current["completedAt"] = iso()
                write_json(run_dir / "plan.json", current)

            seen = set()
            for path in (run_dir / "events").glob("*.jsonl"):
                try:
                    for line in path.read_text(encoding="utf-8").splitlines():
                        try:
                            seen.add(json.loads(line).get("uuid"))
                        except Exception:
                            continue
                except OSError:
                    continue
            accepted = 0
            duplicate = 0
            for event in payload.get("events") or []:
                event = dict(event or {})
                event.setdefault("agent", "remote")
                if "ts" not in event:
                    event["ts"] = iso()
                event["uuid"] = event.get("uuid") or uuid.uuid4().hex
                if event["uuid"] in seen:
                    duplicate += 1
                    continue
                seen.add(event["uuid"])
                try:
                    append_event(run_dir, event)
                except Exception as exc:
                    return 400, {"ok": False, "error": f"bad event: {exc}"}
                accepted += 1
            render_run(run_dir)
        return 200, {
            "ok": True, "accepted": accepted, "duplicate": duplicate,
            "projectId": project_id, "runId": run_id,
        }


class Handler(BaseHTTPRequestHandler):
    server_version = f"live-progress/{VERSION}"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # keep the console quiet
        pass

    @property
    def hub(self) -> Hub:
        return self.server.hub  # type: ignore[attr-defined]

    def _send(self, status: int, body: bytes, content_type: str,
              extra_headers: dict | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for key, value in (extra_headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _send_json(self, status: int, obj) -> None:
        self._send(status, json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8")

    def _read_body(self) -> bytes:
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0:
            return b""
        return self.rfile.read(min(length, 8 * 1024 * 1024))

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        if path == "/api/health":
            self._send_json(200, {"ok": True, "version": VERSION})
            return
        if path == "/api/state":
            text = self.hub.state_text or self.hub._dump(build_global_state(self.hub.home))
            self._send(200, text.encode("utf-8"), "application/json; charset=utf-8")
            return
        if path == "/api/stream":
            self._handle_stream()
            return
        if path == "/api/ingest":
            raw = (query.get("payload") or query.get("data") or [""])[0]
            if not raw:
                self._send_json(400, {"ok": False, "error": "payload is required"})
                return
            try:
                payload = json.loads(raw)
            except Exception as exc:
                self._send_json(400, {"ok": False, "error": f"invalid JSON: {exc}"})
                return
            status, obj = self.hub.ingest(payload)
            self._send_json(status, obj)
            return
        if path == "/favicon.ico":
            self._send(204, b"", "image/x-icon")
            return
        if not path.startswith("/api/"):
            # SPA fallback: the page routes unknown paths itself
            self._serve_template()
            return
        self._send_json(404, {"ok": False, "error": "not found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/presence":
            try:
                payload = json.loads(self._read_body() or b"{}")
            except Exception:
                payload = {}
            client_id = str(payload.get("clientId") or payload.get("client_id") or "")
            if client_id:
                self.hub.touch_presence(client_id)
            self._send_json(200, {"ok": True})
            return
        if parsed.path == "/api/ingest":
            try:
                payload = json.loads(self._read_body() or b"{}")
            except Exception as exc:
                self._send_json(400, {"ok": False, "error": f"invalid JSON: {exc}"})
                return
            status, obj = self.hub.ingest(payload)
            self._send_json(status, obj)
            return
        self._send_json(404, {"ok": False, "error": "not found"})

    def _serve_template(self):
        try:
            body = self.hub.template.read_bytes()
        except OSError:
            body = ("<!doctype html><meta charset=utf-8><h1>live-progress</h1>"
                    "<p>模板缺失：{}</p>".format(self.hub.template)).encode("utf-8")
        self._send(200, body, "text/html; charset=utf-8")

    def _handle_stream(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        queue = self.hub.register_client()
        try:
            initial = self.hub.state_text or self.hub._dump(build_global_state(self.hub.home))
            self.wfile.write(f"event: state\ndata: {initial}\n\n".encode("utf-8"))
            self.wfile.flush()
            while not self.hub.stop.is_set():
                try:
                    event, data = queue.get(timeout=15)
                except Empty:
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
                    continue
                self.wfile.write(f"event: {event}\ndata: {data}\n\n".encode("utf-8"))
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            self.hub.unregister_client(queue)


class HubServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def cmd_serve(args) -> int:
    home = resolve_home(args)
    home.mkdir(parents=True, exist_ok=True)
    template = Path(args.template).expanduser().resolve() if args.template else \
        Path(__file__).resolve().parent.parent / "templates" / "board.html"
    host = args.host or DEFAULT_HOST
    if host not in ("127.0.0.1", "localhost", "::1") and not args.allow_remote:
        print("refusing to bind non-loopback host without --allow-remote", file=sys.stderr)
        return 2
    hub = Hub(home, template, notify=not args.no_notify)
    hub.start()
    port = args.port
    server = None
    last_error = None
    for candidate in [port] + [port + i for i in range(1, 20)]:
        try:
            server = HubServer((host, candidate), Handler)
            port = candidate
            break
        except OSError as exc:
            last_error = exc
            continue
    if server is None:
        print(f"cannot bind: {last_error}", file=sys.stderr)
        return 2
    server.hub = hub  # type: ignore[attr-defined]
    browser_host = "127.0.0.1" if host in ("0.0.0.0", "::") else host
    url = f"http://{browser_host}:{port}/"
    write_json(home / "hub.json", {
        "url": url, "host": host, "port": port, "pid": os.getpid(),
        "startedAt": iso(), "version": VERSION,
    })
    print(f"live-progress board: {url}")
    print(f"home: {home}")
    print(f"template: {template}")
    sys.stdout.flush()
    if args.open:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        hub.shutdown()
        server.shutdown()
        server.server_close()
        try:
            (home / "hub.json").unlink()
        except OSError:
            pass
    return 0


# ------------------------------------------------------------------------- commands

def _load_plan_file(path: str) -> dict:
    if path == "-":
        return json.load(sys.stdin)
    return json.loads(Path(path).expanduser().read_text(encoding="utf-8"))


def _print_run_summary(view: dict, args) -> None:
    if getattr(args, "json_out", False):
        print(json.dumps(view, ensure_ascii=False, indent=2))
        return
    progress = view["progress"]
    print(f"任务: {view['title']} [{STATUS_ZH.get(view['status'], view['status'])}] "
          f"计划 v{view['revision']}  进度 {progress['done']}/{progress['total']} "
          f"({progress['percent']}%)  并行 {progress['inProgress']}")
    print(f"运行: {view['id']}  更新: {fmt_ago(ago_sec(view.get('updatedAt')))}")
    print("代理:")
    for agent in view["agents"]:
        current = agent.get("currentText") or "—"
        print(f"  {agent['name']:<10} {STATUS_ZH.get(agent['status'], agent['status']):<6} "
              f"{current}  (最后事件 {fmt_ago(agent.get('lastSeenAgoSec'))})")
    print("步骤:")
    for step in view["steps"]:
        print(f"  {step['id']:<8} {STATUS_ZH.get(step['status'], step['status']):<6} "
              f"{step['owner']:<10} {step['title']}  "
              f"({fmt_duration(step.get('elapsedMs'))})")


def cmd_init(args) -> int:
    root = resolve_root(args)
    home = resolve_home(args)
    project_id = slugify(args.project_id, "project")
    run_id = slugify(args.run or f"{now_dt().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:4]}", "run")
    run_dir = runs_path(root) / run_id
    (run_dir / "events").mkdir(parents=True, exist_ok=True)
    raw = _load_plan_file(args.plan_file)
    plan = normalize_plan(raw, run_id)
    plan.update({
        "projectId": project_id,
        "revision": 1,
        "status": "running",
        "createdAt": iso(),
        "updatedAt": iso(),
        "completedAt": None,
        "changes": [{
            "rev": 1, "at": iso(), "by": "lead",
            "reason": str(raw.get("reason") or "初版计划"),
            "added": [step["id"] for step in plan["steps"]],
            "removed": [], "changed": [],
        }],
    })
    write_json(run_dir / "plan.json", plan)
    append_event(run_dir, {"agent": "lead", "type": "init", "note": "计划 v1"})
    if not args.no_register:
        register_project(home, project_id, name=args.name or project_id,
                         color=args.color, kind="local", path=root)
    view = render_run(run_dir)
    if args.json_out:
        print(json.dumps({"runId": run_id, "projectId": project_id, "dir": str(run_dir),
                          "view": view}, ensure_ascii=False, indent=2))
    else:
        print(f"run: {run_id}")
        print(f"dir: {run_dir}")
        print(f"project: {project_id}")
        print(f"看板: http://127.0.0.1:{DEFAULT_PORT}/r/{project_id}/{run_id}")
    return 0


def _require_run(args) -> Path:
    root = resolve_root(args)
    run_dir = resolve_run(root, getattr(args, "run", None))
    if not run_dir:
        raise SystemExit(f"no run found under {root} (run init first)")
    return run_dir


def _find_step(plan: dict, step_id: str) -> dict:
    for step in plan.get("steps") or []:
        if step["id"] == step_id:
            return step
    raise SystemExit(f"unknown step: {step_id}")


def cmd_start(args) -> int:
    run_dir = _require_run(args)
    plan = load_plan(run_dir) or {}
    step = _find_step(plan, slugify(args.step, "s"))
    view = build_run_view(run_dir) or {}
    current = next((item for item in view.get("steps", []) if item["id"] == step["id"]), None)
    if current and current["status"] in TERMINAL_STEPS and not args.force:
        raise SystemExit(f"step {step['id']} is already {current['status']} (use --force)")
    agent = slugify(args.agent or step["owner"], "agent")
    if agent != step["owner"] and agent != "lead" and not args.force:
        raise SystemExit(f"step {step['id']} is owned by {step['owner']}; revise the plan or use --force")
    append_event(run_dir, {
        "agent": agent, "type": "start", "stepId": step["id"],
        "note": args.note or "",
    })
    maybe_render(run_dir, args)
    print(f"start {step['id']} ({step['title']}) by {agent}")
    return 0


def cmd_done(args) -> int:
    run_dir = _require_run(args)
    plan = load_plan(run_dir) or {}
    step = _find_step(plan, slugify(args.step, "s"))
    agent = slugify(args.agent or step["owner"], "agent")
    append_event(run_dir, {
        "agent": agent, "type": "done", "stepId": step["id"],
        "note": args.note or "", "evidence": list(args.evidence or []),
    })
    if args.start:
        next_step = _find_step(plan, slugify(args.start, "s"))
        append_event(run_dir, {
            "agent": slugify(args.next_agent or agent, "agent"),
            "type": "start", "stepId": next_step["id"], "note": "",
        })
    maybe_render(run_dir, args)
    print(f"done {step['id']} ({step['title']}) by {agent}")
    if args.start:
        print(f"start {next_step['id']} ({next_step['title']})")
    return 0


def _terminal_cmd(args, event_type: str, label: str) -> int:
    run_dir = _require_run(args)
    plan = load_plan(run_dir) or {}
    step = _find_step(plan, slugify(args.step, "s"))
    agent = slugify(args.agent or step["owner"], "agent")
    append_event(run_dir, {
        "agent": agent, "type": event_type, "stepId": step["id"],
        "note": args.reason or "", "evidence": list(getattr(args, "evidence", []) or []),
    })
    maybe_render(run_dir, args)
    print(f"{label} {step['id']} ({step['title']}) by {agent}")
    return 0


def cmd_block(args) -> int:
    return _terminal_cmd(args, "block", "block")


def cmd_fail(args) -> int:
    return _terminal_cmd(args, "fail", "fail")


def cmd_skip(args) -> int:
    return _terminal_cmd(args, "skip", "skip")


def cmd_resume(args) -> int:
    return _terminal_cmd(args, "resume", "resume")


def cmd_heartbeat(args) -> int:
    run_dir = _require_run(args)
    append_event(run_dir, {
        "agent": slugify(args.agent, "agent"), "type": "heartbeat",
        "stepId": slugify(args.step, "s") if args.step else None,
        "current": args.current or "",
    })
    maybe_render(run_dir, args)
    print("heartbeat")
    return 0


def _terminate_process_group(proc) -> None:
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except Exception:
        try:
            proc.terminate()
        except Exception:
            return
    try:
        proc.wait(timeout=3)
        return
    except Exception:
        pass
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def cmd_exec(args) -> int:
    """Run a command and record the whole lifecycle on one step.

    start -> periodic heartbeat (with the last output line) -> done/fail.
    This is what makes background jobs and long commands account for themselves
    instead of relying on the agent to poll and remember.
    """
    run_dir = _require_run(args)
    plan = load_plan(run_dir) or {}
    step = _find_step(plan, slugify(args.step, "s"))
    agent = slugify(args.agent or step["owner"], "agent")
    if agent != step["owner"] and agent != "lead" and not args.force:
        raise SystemExit(f"step {step['id']} is owned by {step['owner']}; revise the plan or use --force")
    view = build_run_view(run_dir) or {}
    current = next((item for item in view.get("steps", []) if item["id"] == step["id"]), None)
    if current and current["status"] in TERMINAL_STEPS and not args.force:
        raise SystemExit(f"step {step['id']} is already {current['status']} (use --force)")

    command = list(args.command or [])
    while command and command[0] == "--":
        command = command[1:]
    if not command:
        raise SystemExit("exec needs a command, e.g. board.py exec s5 --agent bg-1 -- pytest -q")
    label = args.label or " ".join(command)
    started = now_dt()
    started_ts = iso(started)
    log_path = Path(args.log).expanduser().resolve() if args.log else \
        run_dir / "exec" / f"{step['id']}-{started.strftime('%H%M%S')}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as log:
        log.write(f"# live-progress exec\n# step: {step['id']} ({step['title']})\n"
                  f"# agent: {agent}\n# started: {started_ts}\n# command: {' '.join(command)}\n\n")

    append_event(run_dir, {
        "agent": agent, "type": "start", "stepId": step["id"],
        "note": args.note or "", "command": " ".join(command),
    })
    maybe_render(run_dir, args)

    env = dict(os.environ)
    env.setdefault("PYTHONUNBUFFERED", "1")
    try:
        proc = subprocess.Popen(
            command, cwd=args.cwd or None, env=env, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            bufsize=1, start_new_session=True,
        )
    except OSError as exc:
        append_event(run_dir, {
            "agent": agent, "type": "fail", "stepId": step["id"],
            "note": f"spawn failed: {exc}", "evidence": [str(log_path)],
        })
        maybe_render(run_dir, args)
        raise SystemExit(f"exec: cannot start command: {exc}")

    tail = {"last": ""}

    def pump():
        try:
            with open(log_path, "a", encoding="utf-8") as log:
                for line in proc.stdout:
                    log.write(line)
                    log.flush()
                    tail["last"] = line.rstrip()[:140]
                    if not args.quiet:
                        sys.stdout.write(line)
                        sys.stdout.flush()
        except Exception as exc:  # pragma: no cover - defensive
            tail["last"] = f"reader error: {exc}"

    reader = threading.Thread(target=pump, name="exec-output", daemon=True)
    reader.start()

    heartbeat = max(0.2, float(args.heartbeat or 0))
    deadline = time.time() + args.timeout if args.timeout else None
    timed_out = False
    interrupted = False
    exit_code = None
    try:
        while True:
            wait_for = heartbeat
            if deadline:
                remaining = deadline - time.time()
                if remaining <= 0:
                    timed_out = True
                    break
                wait_for = min(wait_for, max(0.05, remaining))
            try:
                exit_code = proc.wait(timeout=wait_for)
                break
            except subprocess.TimeoutExpired:
                if deadline and time.time() >= deadline:
                    timed_out = True
                    break
                elapsed = int((now_dt() - started).total_seconds())
                detail = f" · {tail['last']}" if tail["last"] else ""
                append_event(run_dir, {
                    "agent": agent, "type": "heartbeat", "stepId": step["id"],
                    "current": f"{label[:80]} 运行中 {elapsed}s{detail}"[:220],
                })
                maybe_render(run_dir, args)
    except KeyboardInterrupt:
        interrupted = True
    finally:
        if timed_out or interrupted:
            _terminate_process_group(proc)
            try:
                exit_code = proc.wait(timeout=3)
            except Exception:
                exit_code = -1
        reader.join(timeout=3)

    duration = int((now_dt() - started).total_seconds())
    with open(log_path, "a", encoding="utf-8") as log:
        log.write(f"\n# finished: {iso()} exit={exit_code} duration={duration}s\n")

    if interrupted:
        status_line = "interrupted"
        append_event(run_dir, {
            "agent": agent, "type": "fail", "stepId": step["id"],
            "note": "interrupted by user", "evidence": [str(log_path)],
        })
        code = 130
    elif timed_out:
        status_line = f"timeout after {args.timeout}s"
        append_event(run_dir, {
            "agent": agent, "type": "fail", "stepId": step["id"],
            "note": f"timeout after {args.timeout}s", "evidence": [str(log_path)],
        })
        code = 124
    elif exit_code == 0:
        status_line = f"exit 0 · {duration}s"
        append_event(run_dir, {
            "agent": agent, "type": "done", "stepId": step["id"],
            "note": args.note or status_line, "evidence": [str(log_path)],
        })
        code = 0
    else:
        status_line = f"exit {exit_code} · {duration}s"
        append_event(run_dir, {
            "agent": agent, "type": "fail", "stepId": step["id"],
            "note": f"exit {exit_code}", "evidence": [str(log_path)],
        })
        code = int(exit_code) if isinstance(exit_code, int) and exit_code > 0 else 1

    maybe_render(run_dir, args)
    print(f"[live-progress] step {step['id']} {status_line}; log: {log_path}")
    return code


def cmd_agent(args) -> int:
    run_dir = _require_run(args)
    plan = load_plan(run_dir) or {}
    agent_id = slugify(args.agent_id, "agent")
    agents = {item["id"]: item for item in plan.get("agents") or []}
    existing = agents.get(agent_id) or make_agent(agent_id)
    existing.update({
        "id": agent_id,
        "name": args.name or existing.get("name") or agent_id,
        "role": args.role or existing.get("role"),
        "color": args.color or existing.get("color"),
        "kind": args.kind or existing.get("kind"),
    })
    agents[agent_id] = existing
    plan["agents"] = list(agents.values())
    plan["updatedAt"] = iso()
    save_plan(run_dir, plan)
    maybe_render(run_dir, args)
    print(f"agent {agent_id} updated")
    return 0


def cmd_revise(args) -> int:
    run_dir = _require_run(args)
    old = load_plan(run_dir) or {}
    raw = _load_plan_file(args.plan_file)
    new = normalize_plan(raw, old.get("runId") or run_dir.name)
    old_steps = {step["id"]: step for step in old.get("steps") or []}
    new_ids = {step["id"] for step in new["steps"]}
    added = [sid for sid in new_ids if sid not in old_steps]
    removed = [sid for sid in old_steps if sid not in new_ids]
    changed = []
    for step in new["steps"]:
        previous = old_steps.get(step["id"])
        if not previous:
            continue
        for field in ("title", "owner", "phaseId", "size", "acceptance", "dependsOn"):
            if previous.get(field) != step.get(field):
                changed.append(step["id"])
                break
    for step in new["steps"]:
        if step["id"] in added:
            step["note"] = str(step.get("note") or "")
    revision = int(old.get("revision") or 1) + 1
    for sid in removed:
        cancelled = dict(old_steps[sid])
        cancelled["superseded"] = True
        cancelled["note"] = f"rev{revision}: {args.reason}"
        if cancelled["phaseId"] not in {phase["id"] for phase in new["phases"]}:
            new["phases"].append({"id": cancelled["phaseId"], "title": cancelled["phaseId"]})
        new["steps"].append(cancelled)
    merged_agents = {agent["id"]: agent for agent in old.get("agents") or []}
    for agent in new["agents"]:
        merged_agents[agent["id"]] = agent
    new["agents"] = list(merged_agents.values())
    changes = list(old.get("changes") or [])
    changes.append({
        "rev": revision, "at": iso(), "by": args.by or "lead",
        "reason": args.reason, "added": added, "removed": removed,
        "changed": sorted(set(changed)),
    })
    new.update({
        "projectId": old.get("projectId"),
        "runId": old.get("runId") or run_dir.name,
        "revision": revision,
        "status": old.get("status", "running"),
        "createdAt": old.get("createdAt"),
        "updatedAt": iso(),
        "completedAt": old.get("completedAt"),
        "changes": changes,
    })
    save_plan(run_dir, new)
    append_event(run_dir, {
        "agent": slugify(args.by or "lead", "agent"), "type": "plan_revise",
        "note": args.reason,
    })
    maybe_render(run_dir, args)
    print(f"plan revised to v{revision} (added={added}, removed={removed}, changed={sorted(set(changed))})")
    return 0


def cmd_close(args) -> int:
    run_dir = _require_run(args)
    plan = load_plan(run_dir) or {}
    view = build_run_view(run_dir)
    open_steps = [step["id"] for step in (view or {}).get("steps", [])
                  if step["status"] in OPEN_STEPS]
    if open_steps and not args.force:
        raise SystemExit(f"cannot close: steps not terminal: {', '.join(open_steps)} (use --force)")
    plan["status"] = "completed"
    plan["completedAt"] = iso()
    plan["updatedAt"] = iso()
    save_plan(run_dir, plan)
    append_event(run_dir, {
        "agent": slugify(args.by or "lead", "agent"), "type": "run_close",
        "note": f"关闭运行，遗留未终态步骤 {len(open_steps)} 个" if open_steps else "全部步骤已结束",
    })
    maybe_render(run_dir, args)
    print(f"run closed: {run_dir.name} ({'forced' if open_steps and args.force else 'clean'})")
    return 0


def cmd_status(args) -> int:
    root = resolve_root(args)
    if args.all:
        run_dirs_list = run_dirs(root)
        if not run_dirs_list:
            print("no runs")
            return 0
        for run_dir in run_dirs_list:
            view = build_run_view(run_dir)
            if view:
                print("=" * 72)
                _print_run_summary(view, args)
        return 0
    run_dir = resolve_run(root, args.run)
    if not run_dir:
        print(f"no runs under {root}", file=sys.stderr)
        return 1
    view = build_run_view(run_dir)
    if not view:
        print("plan missing", file=sys.stderr)
        return 1
    _print_run_summary(view, args)
    if not getattr(args, "json_out", False):
        hub = read_json(resolve_home(args) / "hub.json")
        if hub and hub.get("url"):
            print(f"看板: {hub['url']}r/{view['projectId']}/{view['id']}")
    return 0


def cmd_render(args) -> int:
    root = resolve_root(args)
    targets = run_dirs(root) if args.all else [resolve_run(root, args.run)]
    for run_dir in [target for target in targets if target]:
        view = render_run(run_dir)
        if view:
            print(f"rendered {run_dir} -> state.json, BOARD.md")
    return 0


def cmd_project(args) -> int:
    home = resolve_home(args)
    if args.project_cmd == "list":
        projects = list_projects(home)
        if args.json_out:
            print(json.dumps(projects, ensure_ascii=False, indent=2))
        else:
            for project in projects:
                print(f"{project['id']:<24} {project.get('kind'):<7} "
                      f"{project.get('name')}  {project.get('source', {}).get('path', '')}")
        return 0
    if args.project_cmd == "add":
        entry = register_project(home, args.id, name=args.name, color=args.color,
                                 kind=args.kind)
        if args.json_out:
            print(json.dumps(entry, ensure_ascii=False, indent=2))
        else:
            print(f"project: {entry['id']} kind={entry['kind']}")
            if entry.get("token"):
                print(f"token: {entry['token']}")
        return 0
    if args.project_cmd == "remove":
        if unregister_project(home, args.id, purge=args.purge):
            print(f"removed {args.id}")
            return 0
        print(f"unknown project: {args.id}", file=sys.stderr)
        return 1
    return 1


def cmd_push(args) -> int:
    home = resolve_home(args)
    root = resolve_root(args)
    run_dir = resolve_run(root, args.run)
    if not run_dir:
        print(f"no run under {root}", file=sys.stderr)
        return 1
    plan = load_plan(run_dir) or {}
    project_id = slugify(args.project_id or plan.get("projectId") or "", "")
    if not project_id:
        print("project id unknown; pass --project-id", file=sys.stderr)
        return 1
    projects = load_projects(home).get("projects", {})
    project = projects.get(project_id) or {}
    token = args.token or os.environ.get("DSH_PROGRESS_TOKEN") or project.get("token")
    if not token:
        print("no token: pass --token or register an ingest project", file=sys.stderr)
        return 1
    push_file = run_dir / "push-state.json"
    state = read_json(push_file, {}) or {}
    sent = set(state.get("sent") or [])
    events = [event for event in read_events(run_dir)
              if event.get("uuid") and event["uuid"] not in sent]
    payload = {
        "project": {
            "id": project_id,
            "name": project.get("name") or project_id,
            "color": project.get("color") or hash_color(project_id),
        },
        "run": {
            "id": plan.get("runId") or run_dir.name,
            "title": plan.get("title"), "goal": plan.get("goal"),
            "revision": plan.get("revision"), "status": plan.get("status"),
        },
        "plan": plan,
        "events": events,
        "token": token,
    }
    url = args.to.rstrip("/") + "/api/ingest"
    request = Request(url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                      headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=15) as response:
            result = json.loads(response.read().decode("utf-8") or "{}")
    except HTTPError as exc:
        print(f"push failed: HTTP {exc.code} {exc.read().decode('utf-8', 'replace')}", file=sys.stderr)
        return 1
    except URLError as exc:
        print(f"push failed: {exc.reason}", file=sys.stderr)
        return 1
    sent.update(event.get("uuid") for event in events if event.get("uuid"))
    state["sent"] = sorted(sent)[-5000:]
    state["revision"] = plan.get("revision")
    state["pushedAt"] = iso()
    write_json(push_file, state)
    print(json.dumps(result, ensure_ascii=False))
    return 0


# ---------------------------------------------------------------------------- CLI

def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--home", default=argparse.SUPPRESS, help="hub home (default ~/.dsh/progress)")
    common.add_argument("--root", default=argparse.SUPPRESS, help="project progress dir (default ./.dsh/progress)")
    common.add_argument("--json", dest="json_out", action="store_true", default=argparse.SUPPRESS)
    common.add_argument("--no-render", action="store_true", default=argparse.SUPPRESS)

    parser = argparse.ArgumentParser(prog="board.py", description="live-progress board CLI",
                                     parents=[common])
    parser.set_defaults(home=None, root=None, json_out=False, no_render=False)
    parser.add_argument("--version", action="version", version=f"live-progress {VERSION}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", parents=[common], help="create a run from a plan file")
    p.add_argument("--project-id", required=True)
    p.add_argument("--name")
    p.add_argument("--color")
    p.add_argument("--plan-file", required=True)
    p.add_argument("--run")
    p.add_argument("--no-register", action="store_true")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("start", parents=[common], help="mark a step in_progress")
    p.add_argument("step")
    p.add_argument("--agent")
    p.add_argument("--note")
    p.add_argument("--force", action="store_true")
    p.add_argument("--run")
    p.set_defaults(func=cmd_start)

    p = sub.add_parser("done", parents=[common], help="mark a step done")
    p.add_argument("step")
    p.add_argument("--agent")
    p.add_argument("--evidence", action="append")
    p.add_argument("--note")
    p.add_argument("--start", dest="start")
    p.add_argument("--next-agent")
    p.add_argument("--run")
    p.set_defaults(func=cmd_done)

    for name, func in (("block", cmd_block), ("fail", cmd_fail), ("skip", cmd_skip), ("resume", cmd_resume)):
        p = sub.add_parser(name, parents=[common])
        p.add_argument("step")
        p.add_argument("--agent")
        p.add_argument("--reason")
        p.add_argument("--evidence", action="append")
        p.add_argument("--run")
        p.set_defaults(func=func)

    p = sub.add_parser("heartbeat", parents=[common], help="append a liveness line")
    p.add_argument("--agent", required=True)
    p.add_argument("--step")
    p.add_argument("--current")
    p.add_argument("--run")
    p.set_defaults(func=cmd_heartbeat)

    p = sub.add_parser("exec", parents=[common], help="run a command while recording a step")
    p.add_argument("step")
    p.add_argument("--agent")
    p.add_argument("--heartbeat", type=float, default=30.0)
    p.add_argument("--timeout", type=float, default=0.0)
    p.add_argument("--label")
    p.add_argument("--note")
    p.add_argument("--log")
    p.add_argument("--cwd")
    p.add_argument("--quiet", action="store_true")
    p.add_argument("--force", action="store_true")
    p.add_argument("--run")
    p.set_defaults(func=cmd_exec)

    p = sub.add_parser("agent", parents=[common], help="update the agent roster")
    p.add_argument("agent_id")
    p.add_argument("--name")
    p.add_argument("--role")
    p.add_argument("--color")
    p.add_argument("--kind")
    p.add_argument("--run")
    p.set_defaults(func=cmd_agent)

    p = sub.add_parser("revise", parents=[common], help="replace the plan (Lead only)")
    p.add_argument("--plan-file", required=True)
    p.add_argument("--reason", required=True)
    p.add_argument("--by", default="lead")
    p.add_argument("--run")
    p.set_defaults(func=cmd_revise)

    p = sub.add_parser("close", parents=[common], help="close the run")
    p.add_argument("--by", default="lead")
    p.add_argument("--force", action="store_true")
    p.add_argument("--run")
    p.set_defaults(func=cmd_close)

    p = sub.add_parser("status", parents=[common], help="print a run summary")
    p.add_argument("--run")
    p.add_argument("--all", action="store_true")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("render", parents=[common], help="rewrite state.json and BOARD.md")
    p.add_argument("--run")
    p.add_argument("--all", action="store_true")
    p.set_defaults(func=cmd_render)

    p = sub.add_parser("serve", parents=[common], help="start the hub server")
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--host", default=DEFAULT_HOST)
    p.add_argument("--open", action="store_true")
    p.add_argument("--no-notify", action="store_true")
    p.add_argument("--template")
    p.add_argument("--allow-remote", action="store_true")
    p.set_defaults(func=cmd_serve)

    p = sub.add_parser("project", parents=[common], help="manage registered projects")
    p_sub = p.add_subparsers(dest="project_cmd", required=True)
    p_add = p_sub.add_parser("add", parents=[common])
    p_add.add_argument("--id", required=True)
    p_add.add_argument("--name")
    p_add.add_argument("--color")
    p_add.add_argument("--kind", choices=["local", "ingest"], default="ingest")
    p_list = p_sub.add_parser("list", parents=[common])
    p_remove = p_sub.add_parser("remove", parents=[common])
    p_remove.add_argument("id")
    p_remove.add_argument("--purge", action="store_true")
    p.set_defaults(func=cmd_project)

    p = sub.add_parser("push", parents=[common], help="push a local run to a hub")
    p.add_argument("--to", required=True)
    p.add_argument("--project-id")
    p.add_argument("--token")
    p.add_argument("--run")
    p.set_defaults(func=cmd_push)

    return parser


GLOBAL_VALUE_OPTS = {"--home", "--root"}
GLOBAL_FLAG_OPTS = {"--json", "--no-render"}


def extract_globals(argv):
    """Allow --home/--root/--json/--no-render before or after the subcommand."""
    values = {}
    flags = set()
    rest = []
    index = 0
    while index < len(argv):
        token = argv[index]
        if token in GLOBAL_VALUE_OPTS and index + 1 < len(argv):
            values[token[2:]] = argv[index + 1]
            index += 2
            continue
        if token.startswith("--home=") or token.startswith("--root="):
            key, value = token.split("=", 1)
            values[key[2:]] = value
            index += 1
            continue
        if token in GLOBAL_FLAG_OPTS:
            flags.add("json_out" if token == "--json" else "no_render")
            index += 1
            continue
        if token == "--":
            rest.extend(argv[index:])
            break
        rest.append(token)
        index += 1
    return values, flags, rest


def main(argv=None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    values, flags, rest = extract_globals(raw)
    wrapped = None
    if "--" in rest:
        cut = rest.index("--")
        wrapped = rest[cut + 1:]
        rest = rest[:cut]
    parser = build_parser()
    args = parser.parse_args(rest)
    args.command = wrapped or []
    for key, value in values.items():
        setattr(args, key, value)
    for key in flags:
        setattr(args, key, True)
    try:
        return int(args.func(args) or 0)
    except BrokenPipeError:
        return 0
    except KeyboardInterrupt:
        return 130
    except SystemExit:
        raise
    except Exception as exc:
        print(f"board.py: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
