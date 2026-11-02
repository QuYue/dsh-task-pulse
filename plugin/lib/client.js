window.__ModuleLoader__.load({
  id: "dsh-live-progress-card",
  factory: (require) => {
    var module = { exports: {} };
    var exports = module.exports;
    Object.defineProperty(exports, Symbol.toStringTag, { value: "Module" });
    const React = require("react");
    const h = React.createElement;

    const CSS = `
.dsh-lp-card {
  box-sizing: border-box; width: 100%; margin: 0 0 8px; padding: 0;
  border: 1px solid var(--dsw-alias-border-l2, rgba(255,255,255,.12));
  border-radius: 10px;
  background: var(--dsw-alias-bg-l1, #131a25);
  color: var(--dsw-alias-label-primary, #e6edf3);
  font-size: 12px; line-height: 1.5;
  box-shadow: 0 1px 2px rgba(0,0,0,.18);
}
.dsh-lp-head { padding: 6px 10px 7px; cursor: pointer; user-select: none; }
.dsh-lp-head:hover { background: rgba(127,127,127,.06); border-radius: 9px; }
.dsh-lp-line1 { display: flex; align-items: center; gap: 6px; }
.dsh-lp-line2 { display: flex; align-items: center; gap: 8px; margin-top: 4px; padding-left: 13px; }
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
.dsh-lp-title { overflow-wrap: anywhere; }
.dsh-lp-owner { white-space: nowrap; }
.dsh-lp-time { white-space: nowrap; color: var(--dsw-alias-label-tertiary, #8b98ab); font-variant-numeric: tabular-nums; }
.dsh-lp-progress { display: flex; align-items: center; gap: 4px; }
.dsh-lp-track {
  width: 46px; height: 4px; border-radius: 999px; background: rgba(127,127,127,.22); overflow: hidden; flex: none;
}
.dsh-lp-fill { height: 100%; border-radius: 999px; background: #4f8cff; }
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

    // B1 static sample; B2 replaces this with hub data.
    const SAMPLE = {
      name: "18:40 · 步骤表内联进度",
      status: "doing",
      done: 2,
      total: 5,
      percent: 60,
      elapsed: "12m",
      steps: [
        { id: "s1", size: "S", title: "调整 size/进度布局", status: "done", owner: "lead", progress: null, start: "18:40:12", end: "18:44:03", elapsed: "3m51s" },
        { id: "s2", size: "M", title: "压缩行高与进度条展示", status: "done", owner: "lead", progress: null, start: "18:44:03", end: "18:52:20", elapsed: "8m17s" },
        { id: "s3", size: "S", title: "增加开始/结束时间列", status: "doing", owner: "coder", progress: 45, start: "18:52:20", end: "", elapsed: "3m", note: "等待接口字段确认" },
        { id: "s4", size: "S", title: "补充 v2 文档", status: "wait", owner: "", progress: null, start: "", end: "", elapsed: "" },
        { id: "s5", size: "S", title: "测试与页面校验", status: "wait", owner: "", progress: null, start: "", end: "", elapsed: "" }
      ]
    };

    const STATUS = {
      done: { label: "完成", dot: "dsh-lp-dot-done", color: "#3ddc97" },
      doing: { label: "进行", dot: "dsh-lp-dot-doing", color: "#4f8cff" },
      wait: { label: "等待", dot: "dsh-lp-dot-wait", color: "#8892a6" },
      fail: { label: "失败", dot: "dsh-lp-dot-fail", color: "#ff5f6d" }
    };

    function statusOf(step) { return STATUS[step.status] || STATUS.wait; }

    function progressCell(step) {
      if (step.progress == null) return h("span", { className: "dsh-lp-time" }, "—");
      return h("span", { className: "dsh-lp-progress" },
        h("span", { className: "dsh-lp-track" },
          h("span", { className: "dsh-lp-fill", style: { width: Math.max(0, Math.min(100, step.progress)) + "%" } })
        ),
        h("span", { className: "dsh-lp-pct" }, step.progress + "%")
      );
    }

    function LiveProgressCard() {
      ensureStyles();
      const [open, setOpen] = React.useState(false);
      const [notes, setNotes] = React.useState({});
      const meta = STATUS[SAMPLE.status] || STATUS.wait;
      const toggle = () => setOpen((v) => !v);
      const toggleNote = (id) => setNotes((prev) => Object.assign({}, prev, { [id]: !prev[id] }));

      const currentStep = SAMPLE.steps.find((step) => step.status === "doing");
      const doneCount = SAMPLE.steps.filter((step) => step.status === "done").length;
      const totalCount = SAMPLE.steps.length;
      const taskPct = totalCount ? Math.round(doneCount / totalCount * 100) : 0;
      const barPct = Math.max(0, Math.min(100, taskPct));
      const head = h("div", { className: "dsh-lp-head", role: "button", tabIndex: 0,
        title: open ? "收起任务进度" : "展开任务进度",
        onClick: toggle,
        onKeyDown: (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(); } } },
        h("div", { className: "dsh-lp-line1" },
          h("span", { className: "dsh-lp-dot " + meta.dot }),
          h("span", { className: "dsh-lp-name" }, SAMPLE.name),
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
          currentStep && currentStep.progress != null
            ? h("span", { className: "dsh-lp-step-progress" },
                h("span", { className: "dsh-lp-bar" },
                  h("span", { className: "dsh-lp-bar-fill",
                    style: { width: Math.max(0, Math.min(100, currentStep.progress)) + "%" } })
                ),
                h("span", { className: "dsh-lp-summary-pct" }, currentStep.progress + "%")
              )
            : null,
          h("span", { className: "dsh-lp-current" },
            currentStep ? ("正在：" + currentStep.id + " " + currentStep.title) : "等待下一步")
        )
      );

      let body = null;
      if (open) {
        const rows = SAMPLE.steps.map((step) => {
          const st = statusOf(step);
          const cells = [
            h("td", { key: "st", style: { color: st.color, whiteSpace: "nowrap" } }, st.label),
            h("td", { key: "title" },
              h("span", { className: "dsh-lp-id" }, step.id + " | " + step.size),
              h("span", { className: "dsh-lp-title" }, step.title),
              step.note ? h("button", { key: "note", type: "button", className: "dsh-lp-note-mark",
                onClick: (e) => { e.stopPropagation(); toggleNote(step.id); } }, "注") : null
            ),
            h("td", { key: "owner", className: "dsh-lp-owner" }, step.owner || "—"),
            h("td", { key: "progress" }, progressCell(step)),
            h("td", { key: "time", className: "dsh-lp-time" }, (step.start || "—") + (step.end ? " – " + step.end : "")),
            h("td", { key: "elapsed", className: "dsh-lp-time" }, step.elapsed || "—")
          ];
          const noteRow = step.note && notes[step.id]
            ? h("tr", { key: "note-" + step.id }, h("td", { colSpan: 6 }, h("div", { className: "dsh-lp-note" }, "备注：" + step.note)))
            : null;
          return [h("tr", { key: step.id }, cells), noteRow];
        });

        body = h("div", { className: "dsh-lp-body" },
          h("div", { className: "dsh-lp-meta" }, "用时 " + SAMPLE.elapsed + " · 步骤 " + SAMPLE.steps.length + " 个"),
          h("div", { className: "dsh-lp-table-wrap" + (SAMPLE.steps.length > 10 ? " dsh-lp-scroll" : "") },
            h("table", { className: "dsh-lp-table" },
              h("thead", null, h("tr", null,
                ["状态", "步骤", "执行者", "进度", "开始/结束", "耗时"].map((label) => h("th", { key: label }, label))
              )),
              h("tbody", null, rows)
            )
          ),
          h("div", { className: "dsh-lp-actions" },
            h("a", { className: "dsh-lp-link", href: "http://127.0.0.1:8770/", target: "_blank", rel: "noreferrer" }, "打开完整看板 8770"),
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
          id: "live-progress-card",
          order: 1
        }, LiveProgressCard)
      );
    }

    exports.apply = apply;
    exports.inject = inject;
    return module.exports;
  }
});
