window.__ModuleLoader__.load({
  id: "@quyue/dsh-task-pulse",
  factory: (require) => {
    var module = { exports: {} };
    var exports = module.exports;
    Object.defineProperty(exports, Symbol.toStringTag, { value: "Module" });
    const React = require("react");
    const h = React.createElement;

    const CSS = `
.dsh-lp-card {
  box-sizing: border-box;
  width: calc(100% - var(--dsh-composer-side-clearance) - var(--dsh-composer-side-clearance) - var(--dsh-composer-dock-inset) - var(--dsh-composer-dock-inset) - var(--dsh-composer-dock-inset) - var(--dsh-composer-dock-inset));
  max-width: calc(var(--dsh-composer-card-max-width) - var(--dsh-composer-dock-inset) - var(--dsh-composer-dock-inset) - var(--dsh-composer-dock-inset) - var(--dsh-composer-dock-inset));
  margin: 0 auto 8px; padding: 0; flex: none;
  border: 0;
  border-radius: var(--dsw-radius-xl, 20px);
  background: var(--dsw-specific-input-major, #1a2230);
  color: var(--dsw-alias-label-primary, #e6edf3);
  font-size: 12px; line-height: 1.5;
  box-shadow: 0 1px 2px rgba(0,0,0,.18);
}
.dsh-lp-head { padding: 6px 10px 7px; cursor: pointer; user-select: none; }
.dsh-lp-head:hover { background: rgba(127,127,127,.06); border-radius: 9px; }
.dsh-lp-line1 { display: flex; align-items: center; gap: 6px; }
.dsh-lp-line2 { display: flex; flex-direction: column; gap: 3px; margin-top: 4px; padding-left: 13px; }
.dsh-lp-active-row { display: flex; align-items: center; gap: 6px; min-width: 0; }
.dsh-lp-state {
  display: inline-flex; align-items: center; gap: 4px; flex: none;
  font-size: 10.5px; color: #8fc1ff; background: rgba(79,140,255,.12);
  border: 1px solid rgba(79,140,255,.3); border-radius: 4px; padding: 0 5px;
}
.dsh-lp-state .dsh-lp-dot { width: 5px; height: 5px; }
.dsh-lp-step-name {
  min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  color: var(--dsw-alias-label-tertiary, #8b98ab); font-size: 11px;
}
.dsh-lp-current {
  min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  color: var(--dsw-alias-label-tertiary, #8b98ab); font-size: 11px;
}
.dsh-lp-bar {
  width: 64px; flex: none; height: 4px; border-radius: 999px;
  background: rgba(127,127,127,.22); overflow: hidden;
}
.dsh-lp-bar-fill { display: block; height: 100%; border-radius: 999px; background: #4f8cff; }
.dsh-lp-dot { width: 7px; height: 7px; border-radius: 50%; flex: none; }
.dsh-lp-dot-done { background: #3ddc97; }
.dsh-lp-dot-doing { background: #4f8cff; animation: dsh-lp-pulse 1.6s infinite; }
.dsh-lp-dot-wait { background: #8892a6; }
.dsh-lp-dot-fail { background: #ff5f6d; }
@keyframes dsh-lp-pulse { 50% { opacity: .35; } }
.dsh-lp-name {
  min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  font-weight: 600;
}
.dsh-lp-summary {
  margin-left: auto; flex: none; color: var(--dsw-alias-label-tertiary, #8b98ab);
  font-size: 11px; white-space: nowrap;
  display: flex; align-items: center; gap: 6px;
}
.dsh-lp-summary-pct { color: var(--dsw-alias-label-secondary, #cfd9e6); font-variant-numeric: tabular-nums; }
.dsh-lp-count { color: var(--dsw-alias-label-tertiary, #8b98ab); font-variant-numeric: tabular-nums; }
.dsh-lp-step-progress { display: flex; align-items: center; gap: 4px; flex: none; }
.dsh-lp-line2 .dsh-lp-bar { width: 56px; }
.dsh-lp-line2 .dsh-lp-bar-fill { background: #3ddc97; }
.dsh-lp-table-wrap { width: 100%; }
.dsh-lp-table-wrap.dsh-lp-scroll {
  max-height: 300px; overflow-y: auto; overscroll-behavior: contain;
  scrollbar-width: thin; scrollbar-color: rgba(127,127,127,.45) transparent;
}
.dsh-lp-table-wrap.dsh-lp-scroll::-webkit-scrollbar { width: 6px; }
.dsh-lp-table-wrap.dsh-lp-scroll::-webkit-scrollbar-thumb {
  background: rgba(127,127,127,.45); border-radius: 999px;
}
.dsh-lp-table-wrap.dsh-lp-scroll::-webkit-scrollbar-track { background: transparent; }
.dsh-lp-chevron { flex: none; color: var(--dsw-alias-label-tertiary, #8b98ab); font-size: 11px; }
.dsh-lp-body {
  border-top: 1px solid var(--dsw-alias-border-l2, rgba(255,255,255,.08));
  padding: 6px 10px 8px;
}
.dsh-lp-meta { color: var(--dsw-alias-label-tertiary, #8b98ab); font-size: 11px; margin-bottom: 3px; }
.dsh-lp-table { width: 100%; border-collapse: collapse; font-size: 11px; }
.dsh-lp-table th {
  text-align: left; font-weight: 500; color: var(--dsw-alias-label-tertiary, #8b98ab);
  font-size: 10px; padding: 2px 4px; border-bottom: 1px solid var(--dsw-alias-border-l2, rgba(255,255,255,.08));
  white-space: nowrap;
}
.dsh-lp-table td { padding: 3px 4px; border-bottom: 1px solid rgba(127,127,127,.08); vertical-align: middle; }
.dsh-lp-table tr:last-child td { border-bottom: 0; }
.dsh-lp-id {
  font-family: var(--dsw-font-mono, ui-monospace, Menlo, monospace);
  font-size: 10px; color: var(--dsw-alias-label-tertiary, #8b98ab);
  background: rgba(127,127,127,.12); border-radius: 4px; padding: 0 4px; margin-right: 4px;
}
.dsh-lp-inline-progress {
  display: inline-flex; align-items: center; gap: 4px;
  margin-right: 4px; vertical-align: middle;
}
.dsh-lp-title { overflow-wrap: anywhere; }
.dsh-lp-owner { white-space: nowrap; }
.dsh-lp-time { white-space: nowrap; color: var(--dsw-alias-label-tertiary, #8b98ab); font-variant-numeric: tabular-nums; }
.dsh-lp-progress { display: flex; align-items: center; gap: 4px; }
.dsh-lp-track {
  display: inline-block; width: 46px; height: 4px; border-radius: 999px;
  background: rgba(127,127,127,.22); overflow: hidden; flex: none; vertical-align: middle;
}
.dsh-lp-fill { display: block; height: 100%; border-radius: 999px; background: #4f8cff; }
.dsh-lp-pct { font-size: 10px; color: var(--dsw-alias-label-secondary, #cfd9e6); font-variant-numeric: tabular-nums; }
.dsh-lp-note-mark {
  margin-left: 4px; font-size: 10px; color: #ffb454;
  background: rgba(255,180,84,.12); border: 1px solid rgba(255,180,84,.35);
  border-radius: 4px; padding: 0 4px; cursor: pointer; font-family: inherit;
}
.dsh-lp-note {
  margin: 3px 0 1px; font-size: 10.5px; color: var(--dsw-alias-label-tertiary, #8b98ab);
  background: rgba(127,127,127,.08); border-left: 2px solid rgba(255,180,84,.5);
  padding: 2px 6px; border-radius: 0 4px 4px 0;
}
.dsh-lp-actions { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: 6px; }
.dsh-lp-link {
  color: #8fc1ff; font-size: 11px; text-decoration: none; cursor: pointer;
}
.dsh-lp-link:hover { text-decoration: underline; }
.dsh-lp-btn {
  font-size: 11px; font-family: inherit; cursor: pointer; color: var(--dsw-alias-label-secondary, #cfd9e6);
  background: transparent; border: 1px solid var(--dsw-alias-border-l2, rgba(255,255,255,.12));
  border-radius: 5px; padding: 1px 7px;
}
.dsh-lp-btn:hover { background: rgba(127,127,127,.12); }
`;

    let stylesReady = false;
    function ensureStyles() {
      if (stylesReady) return;
      try {
        if (document.getElementById("dsh-lp-card-css")) { stylesReady = true; return; }
        const style = document.createElement("style");
        style.id = "dsh-lp-card-css";
        style.textContent = CSS;
        document.head.appendChild(style);
        stylesReady = true;
      } catch (e) { /* ignore */ }
    }

    const HUB_PORTS = [];
    for (let port = 8770; port <= 8789; port += 1) {
      HUB_PORTS.push("http://127.0.0.1:" + port);
    }
    let cachedHub = null;
    const POLL_MS = 1500;
    const BEIJING = new Intl.DateTimeFormat("en-GB", {
      timeZone: "Asia/Shanghai", hour12: false,
      hour: "2-digit", minute: "2-digit", second: "2-digit",
    });

    const STEP_STATUS = {
      done: { label: "完成", dot: "dsh-lp-dot-done", color: "#3ddc97" },
      in_progress: { label: "进行", dot: "dsh-lp-dot-doing", color: "#4f8cff" },
      blocked: { label: "等待", dot: "dsh-lp-dot-wait", color: "#8892a6" },
      pending: { label: "等待", dot: "dsh-lp-dot-wait", color: "#8892a6" },
      failed: { label: "失败", dot: "dsh-lp-dot-fail", color: "#ff5f6d" },
      skipped: { label: "跳过", dot: "dsh-lp-dot-wait", color: "#8892a6" },
      superseded: { label: "已取消", dot: "dsh-lp-dot-wait", color: "#8892a6" },
    };

    function stepMeta(step) { return STEP_STATUS[step.status] || STEP_STATUS.pending; }

    function taskMeta(status) {
      if (status === "completed") return { label: "完成", dot: "dsh-lp-dot-done", color: "#3ddc97" };
      if (status === "failed") return { label: "失败", dot: "dsh-lp-dot-fail", color: "#ff5f6d" };
      if (status === "running") return { label: "进行", dot: "dsh-lp-dot-doing", color: "#4f8cff" };
      return { label: "等待", dot: "dsh-lp-dot-wait", color: "#8892a6" };
    }

    function fmtClock(value) {
      if (!value) return "";
      const date = new Date(value);
      if (isNaN(date.getTime())) return "";
      try { return BEIJING.format(date); } catch (e) { return String(value).slice(11, 19); }
    }

    function fmtDuration(ms) {
      if (ms == null || !isFinite(ms)) return "";
      const sec = Math.max(0, Math.round(ms / 1000));
      if (sec < 60) return sec + "s";
      const min = Math.floor(sec / 60);
      if (min < 60) return min + "m" + (sec % 60 ? " " + (sec % 60) + "s" : "");
      const hour = Math.floor(min / 60);
      return hour + "h" + (min % 60 ? " " + (min % 60) + "m" : "");
    }

    function stepNo(step, index) {
      return step && step.seq != null ? step.seq : index + 1;
    }

    function taskTime(task) {
      const ms = Date.parse((task && (task.startedAt || task.updatedAt)) || "");
      return isFinite(ms) ? ms : 0;
    }

    // Latest task of this session; hidden once the user has submitted a newer prompt.
    function selectTask(state, sessionId, sessionUpdatedAt) {
      if (!state || !sessionId || !Array.isArray(state.projects)) return null;
      const project = state.projects.find((item) => item && (item.id === sessionId || item.sessionId === sessionId));
      if (!project || !Array.isArray(project.runs)) return null;
      const tasks = project.runs.slice().sort((a, b) => taskTime(b) - taskTime(a));
      const preferred = tasks.filter((item) => item && item.isCurrentProject);
      const task = (preferred.length ? preferred : tasks)[0];
      if (!task) return null;
      const started = taskTime(task);
      if (typeof sessionUpdatedAt === "number" && started && started < sessionUpdatedAt) return null;
      return task;
    }

    async function loadHubState(sessionId) {
      if (!sessionId) return null;
      const candidates = [];
      try {
        const override = localStorage.getItem("task-pulse-hub") || localStorage.getItem("dsh-lp-hub");
        if (override) candidates.push(override.replace(/\/$/, ""));
      } catch (e) { /* ignore */ }
      if (cachedHub) candidates.push(cachedHub);
      for (const base of HUB_PORTS) {
        if (candidates.indexOf(base) < 0) candidates.push(base);
      }
      for (const base of candidates) {
        try {
          const response = await fetch(base + "/api/state", { cache: "no-store" });
          if (!response.ok) continue;
          const data = await response.json();
          const projects = Array.isArray(data.projects) ? data.projects : [];
          if (projects.some((project) => project && (project.id === sessionId || project.sessionId === sessionId))) {
            cachedHub = base;
            return { state: data, hub: base };
          }
        } catch (e) { /* try next hub */ }
      }
      cachedHub = null;
      return null;
    }

    function progressCell(step) {
      if (step.progress == null) return h("span", { className: "dsh-lp-time" }, "—");
      return h("span", { className: "dsh-lp-progress" },
        h("span", { className: "dsh-lp-track" },
          h("span", { className: "dsh-lp-fill", style: { width: Math.max(0, Math.min(100, step.progress)) + "%" } })
        ),
        h("span", { className: "dsh-lp-pct" }, step.progress + "%")
      );
    }

    function LiveProgressCard({ sessionId, useSessions }) {
      ensureStyles();
      const useSessionList = typeof useSessions === "function" ? useSessions : null;
      const sessionUpdatedAt = useSessionList
        ? useSessionList((state) => {
            if (!state || !state.byId || !sessionId) return undefined;
            const row = state.byId[sessionId];
            return row ? row.updatedAt : undefined;
          })
        : undefined;

      const [snapshot, setSnapshot] = React.useState(null);
      const storageKey = "task-pulse-card-open:" + (sessionId || "unknown");
      const [open, setOpen] = React.useState(() => {
        try { return localStorage.getItem(storageKey) === "1"; } catch (e) { return false; }
      });
      const [notes, setNotes] = React.useState({});

      React.useEffect(() => {
        try { localStorage.setItem(storageKey, open ? "1" : "0"); } catch (e) { /* ignore */ }
      }, [storageKey, open]);

      React.useEffect(() => {
        if (!sessionId) return undefined;
        let alive = true;
        let timer = null;
        let busy = false;
        const tick = async () => {
          if (!alive || busy) return;
          busy = true;
          try {
            const loaded = await loadHubState(sessionId);
            if (alive) setSnapshot(loaded);
          } catch (e) {
            if (alive) setSnapshot(null);
          } finally {
            busy = false;
            if (alive) timer = setTimeout(tick, POLL_MS);
          }
        };
        tick();
        return () => {
          alive = false;
          if (timer) clearTimeout(timer);
        };
      }, [sessionId]);

      const task = selectTask(snapshot && snapshot.state, sessionId, sessionUpdatedAt);
      if (!task) return null;

      const steps = Array.isArray(task.steps) ? task.steps : [];
      const activeSteps = steps.filter((step) => step.status === "in_progress");
      const progress = task.progress || {};
      const doneCount = progress.done != null ? progress.done : steps.filter((step) => step.status === "done").length;
      const totalCount = progress.total != null ? progress.total : steps.length;
      const taskPct = progress.percent != null
        ? progress.percent
        : (totalCount ? Math.round(doneCount / totalCount * 100) : 0);
      const barPct = Math.max(0, Math.min(100, taskPct));
      const meta = taskMeta(task.status);
      const toggle = () => setOpen((value) => !value);
      const toggleNote = (id) => setNotes((prev) => Object.assign({}, prev, { [id]: !prev[id] }));
      const boardHref = (snapshot.hub || HUB_PORTS[0]) + ((task.urls && task.urls.page) || "/");

      const head = h("div", {
        className: "dsh-lp-head", role: "button", tabIndex: 0,
        "aria-expanded": open ? "true" : "false",
        title: open ? "收起任务进度" : "展开任务进度",
        onClick: toggle,
        onKeyDown: (event) => {
          if (event.key === "Enter" || event.key === " ") { event.preventDefault(); toggle(); }
        },
      },
        h("div", { className: "dsh-lp-line1" },
          h("span", { className: "dsh-lp-dot " + meta.dot }),
          h("span", { className: "dsh-lp-name" }, task.title || task.taskTitle || "当前任务"),
          h("span", { className: "dsh-lp-summary" },
            h("span", null, meta.label),
            h("span", { className: "dsh-lp-bar" },
              h("span", { className: "dsh-lp-bar-fill", style: { width: barPct + "%" } })
            ),
            h("span", { className: "dsh-lp-summary-pct" }, taskPct + "%"),
            h("span", { className: "dsh-lp-count" }, "· " + doneCount + "/" + totalCount)
          ),
          h("span", { className: "dsh-lp-chevron" }, open ? "▾" : "▸")
        ),
        h("div", { className: "dsh-lp-line2" },
          activeSteps.length
            ? activeSteps.map((step) => {
                const state = stepMeta(step);
                return h("div", { className: "dsh-lp-active-row", key: step.id },
                  h("span", { className: "dsh-lp-state" },
                    h("span", { className: "dsh-lp-dot " + state.dot }),
                    h("span", null, state.label)
                  ),
                  step.progress != null
                    ? h("span", { className: "dsh-lp-step-progress" },
                        h("span", { className: "dsh-lp-bar" },
                          h("span", { className: "dsh-lp-bar-fill",
                            style: { width: Math.max(0, Math.min(100, step.progress)) + "%" } })
                        ),
                        h("span", { className: "dsh-lp-summary-pct" }, step.progress + "%")
                      )
                    : null,
                  h("span", { className: "dsh-lp-step-name" },
                    "#" + stepNo(step, steps.indexOf(step)) + " " + step.title)
                );
              })
            : h("span", { className: "dsh-lp-current" },
                task.status === "completed" ? "全部步骤已完成" : "等待下一步")
        )
      );

      let body = null;
      if (open) {
        const rows = steps.map((step, index) => {
          const state = stepMeta(step);
          const cells = [
            h("td", { key: "st", style: { color: state.color, whiteSpace: "nowrap" } }, state.label),
            h("td", { key: "title" },
              h("span", { className: "dsh-lp-id" }, "#" + stepNo(step, index)),
              step.progress != null
                ? h("span", { className: "dsh-lp-inline-progress" },
                    h("span", { className: "dsh-lp-track" },
                      h("span", { className: "dsh-lp-fill",
                        style: { width: Math.max(0, Math.min(100, step.progress)) + "%" } })
                    ),
                    h("span", { className: "dsh-lp-pct" }, step.progress + "%")
                  )
                : null,
              h("span", { className: "dsh-lp-title" }, step.title),
              step.note ? h("button", {
                key: "note", type: "button", className: "dsh-lp-note-mark",
                onClick: (event) => { event.stopPropagation(); toggleNote(step.id); },
              }, "注") : null
            ),
            h("td", { key: "owner", className: "dsh-lp-owner" }, step.owner || "—"),
            h("td", { key: "time", className: "dsh-lp-time" },
              (fmtClock(step.startedAt) || "—") + (step.endedAt ? " – " + fmtClock(step.endedAt) : "")),
            h("td", { key: "elapsed", className: "dsh-lp-time" }, fmtDuration(step.elapsedMs) || "—"),
          ];
          const noteRow = step.note && notes[step.id]
            ? h("tr", { key: "note-" + step.id }, h("td", { colSpan: 5 },
                h("div", { className: "dsh-lp-note" }, "备注：" + step.note)))
            : null;
          return [h("tr", { key: step.id }, cells), noteRow];
        });

        body = h("div", { className: "dsh-lp-body" },
          h("div", { className: "dsh-lp-meta" }, "步骤 " + steps.length + " 个 · 北京时间"),
          h("div", { className: "dsh-lp-table-wrap" + (steps.length > 10 ? " dsh-lp-scroll" : "") },
            h("table", { className: "dsh-lp-table" },
              h("thead", null, h("tr", null,
                ["状态", "步骤", "执行者", "开始/结束", "耗时"].map((label) =>
                  h("th", { key: label }, label))
              )),
              h("tbody", null, rows)
            )
          ),
          h("div", { className: "dsh-lp-actions" },
            h("a", { className: "dsh-lp-link", href: boardHref, target: "_blank", rel: "noreferrer",
              title: "在浏览器打开任务进度表" }, "打开完整看板 8770"),
            h("button", { type: "button", className: "dsh-lp-btn", onClick: toggle }, "收起")
          )
        );
      }

      return h("div", { className: "dsh-lp-card" }, head, body);
    }

    const inject = ["slots"];
    function apply(ctx) {
      ensureStyles();
      ctx.slots.inject("conversation.input.dock", () =>
        ctx.slots.register({
          name: "conversation.input.dock",
          id: "task-pulse-card",
          order: 1
        }, LiveProgressCard)
      );
    }

    exports.apply = apply;
    exports.inject = inject;
    exports.__selectTask = selectTask;
    exports.__taskMeta = taskMeta;
    exports.__stepMeta = stepMeta;
    return module.exports;
  }
});
