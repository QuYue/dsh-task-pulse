# live-progress contract v1

Single source of truth = files. The hub server is a read-only viewer plus an ingest endpoint.
This file is the interface between the backend (`skill/scripts/board.py`) and the page
(`skill/templates/board.html`).

## Layout

```
<root>/.dsh/progress/                     # local progress root
└── sessions/<sessionId>/                  # project = DSH session
    └── tasks/<taskId>/                    # task = one user request
        ├── plan.json                      # Lead-owned, revisioned; has name/taskId/sessionId
        ├── events/<agent>.jsonl           # append-only facts, one file per agent
        ├── state.json                     # rendered snapshot of this task
        └── BOARD.md                       # markdown digest

$DSH_PROGRESS_HOME (default ~/.dsh/progress)   # local hub
├── projects.json                      # registry: id(sessionId)/name/color/kind/source
├── inbox/<sessionId>/tasks/<taskId>/  # mirror materialized from remote ingest
└── hub.log
```

`project.id` is the DSH session id (`session-...`). `project.name` is the DSH auto
session title (or the explicit `--session-title`). `project.kind` is `local` (hub reads
the path directly) or `ingest` (remote pushes into `inbox`).

## CLI (agent-facing)

`python3 skill/scripts/board.py <cmd> ...`

| command | purpose |
|---|---|
| `init --plan-file P [--session-title T] [--name NAME]` | create a task in the current session (name defaults to `HH:MM · plan title`), register the session project |
| `start STEP --agent A` | step -> in_progress |
| `done STEP --agent A [--evidence P]... [--note T] [--start NEXT]` | step -> done, optionally start next |
| `block STEP --agent A --reason T` / `fail ...` / `skip ...` / `resume ...` | terminal / recovery |
| `heartbeat --agent A [--step STEP] [--current T] [--percent N]` | liveness line, optional progress |
| `report STEP --percent N [--agent A] [--current T]` | per-step progress 0-100, no state change |
| `exec STEP --agent A [--heartbeat SEC] [--timeout SEC] [--quiet] -- CMD...` | run a command while recording start/heartbeats/done-or-fail; log is evidence |
| `revise --by lead --reason T --plan-file P` | plan revision++ (Lead only) |
| `status [--json]` | print current snapshot summary |
| `render` | rewrite `state.json` + `BOARD.md` |
| `close [--by lead]` | require terminal steps, mark run completed |
| `prune --keep N [--dry-run] [--yes]` | delete oldest runs beyond N; running runs are skipped |
| `serve [--port 8770] [--home H] [--open]` | hub server |
| `project add/list/remove` | manage ingest projects + tokens |
| `push --to URL --project-id ID` | remote client: push local run deltas to a hub |

Global flags: `--home PATH`, `--root PATH` (progress root; default `./.dsh/progress`),
`--session ID` (default `$DSH_SESSION_ID`),
`--json`, `--no-render`.

## HTTP API

All on the hub (default `http://127.0.0.1:8770`).

| route | method | meaning |
|---|---|---|
| `/` `/p/<pid>` `/r/<pid>/<runId>` | GET | HTML shell (the page routes itself) |
| `/api/state` | GET | full snapshot, see `docs/state.sample.json` |
| `/api/stream` | GET | SSE: `event: state` (full snapshot) and `event: notification` |
| `/api/health` | GET | `{"ok":true}` |
| `/api/presence` | POST | `{"clientId":"..."}` page is open (suppresses OS notifications) |
| `/api/ingest` | POST (JSON body) or GET `?payload=<urlencoded JSON>` | remote push |

Ingest payload:

```json
{
  "project": {"id": "demo-remote", "name": "Demo · 远程任务", "color": "#a06bff"},
  "task": {"id": "20261102-163200-c9d8", "title": "...", "goal": "...", "revision": 1,
           "status": "running", "startedAt": "..."},
  "plan": { ...full plan, required on first push or on revision... },
  "events": [ {"uuid": "...", "ts": "...", "agent": "server-coder", "type": "start", "stepId": "r2"} ],
  "token": "<per-project token from `project add --kind ingest`>"
}
```

Response: `{"ok":true,"accepted":N,"duplicate":M,"projectId":"...","runId":"..."}`.
Dedupe is by event `uuid`; rejected tokens return 403; unknown project returns 404.

Notification SSE payload:

```json
{"id":"notif-uuid","kind":"run_completed|step_failed|step_blocked|plan_revise|stalled",
 "level":"info|warn|error","title":"wordcount · coder 完成 s3",
 "body":"...","projectId":"demo-wordcount","runId":"...","url":"/r/demo-wordcount/...","createdAt":"..."}
```

## Snapshot schema

See `docs/state.sample.json`. Notable fields:

- `projects[].runs[].agents[].status`: `working | idle | blocked | done`; `stalled` bool;
  `lastSeenAgoSec` number; `currentStep` / `currentText` strings.
- `steps[].status`: `pending | in_progress | blocked | done | failed | skipped | superseded`.
- `steps[].progress`: 0-100 or null (latest `report`/`heartbeat --percent`; `done` forces 100).
- `steps[].evidence`: optional paths/URLs proving completion; `note` is free text.
- `runs[].sessionId`, `runs[].taskTitle`, `runs[].title` (task display name with time).
- `steps[].blockedBy`: ids of unfinished dependencies (only meaningful for non-terminal steps).
- `progress.percent` is `round(done / total * 100)`; `total` excludes `skipped`/`superseded`.
- `events` newest first, at most 50; `changes` newest first.

## Page requirements

- Single self-contained HTML file, no external CDN/fonts/scripts.
- Views: overview (`/`) with project cards; detail (`/r/<pid>/<runId>`, `/p/<pid>`) with
  header, agent swimlanes, phase-grouped step table, event stream, plan-change log.
- Live: EventSource `/api/stream`; fall back to polling `/api/state` every 3s on error;
  reconnection with backoff. Elapsed timers tick locally every second.
- Notifications: `event: notification` -> `new Notification(...)` when permission granted;
  button to request permission; dedupe by `id`; click focuses and navigates to `url`.
- POST `/api/presence` every 10s with a random clientId.
- Chinese UI labels, dark theme, responsive down to ~1100px; no raw innerHTML with data.
