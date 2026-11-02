---
name: live-progress
description: 多步任务实时进度看板。文件是唯一事实源：主 agent 维护版本化计划，子 agent 与后台任务追加事件，本地看板网页以泳道 + 步骤表实时显示。适用于需要用户实时监管、有并行 agent / 后台任务 / 远程执行的多步任务。
whenToUse: 任务预计超过约 10 分钟，或会派生子 agent、后台任务，或用户要求“实时进度 / 看板 / 不要只文字汇报”。3 步以内的小任务不必使用。
---

# live-progress

## 心智模型

- **计划**（`plan.json`）：主 agent 写，带 `revision`。回答“要做哪些事、谁负责、依赖谁”。
- **事件**（`events/<agent>.jsonl`）：每个 agent 只追加自己的文件。回答“现在做到哪了”。
- **看板**（`state.json` 快照 + 网页）：由前两者推导，只读。回答“用户此刻看到什么”。

不要在 `plan.json` 里手写状态；状态永远由事件推导。计划结构变更只能通过 `revise`。

> 主 agent 读本文件；子 agent / 后台命令只需读 [`references/record.md`](references/record.md)
> （3 条命令 + `exec` 包装器 + spawn 模板）。

## 何时启用

启用：多步任务、会派生子 agent / 后台 job、远程执行、用户要求实时监管。
不启用：单步琐碎任务；用 `todo_write` 即可。

## 路径与变量

skill 目录通常为以下之一（存在即用）。主协议在本文件，子 agent 的记账协议在 `references/record.md`：

- `.dsh/skills/live-progress`
- `~/.dsh/skills/live-progress`

```bash
BOARD="python3 .dsh/skills/live-progress/scripts/board.py"
```

数据位置：

- 项目运行数据：`<cwd>/.dsh/progress/`（可用 `--root` 改）
- 本地 hub：`~/.dsh/progress`；沙箱内不可写时自动回退到 `<cwd>/.dsh/progress/hub`。
  多命令务必显式传同一个 `--home`，或设置环境变量 `DSH_PROGRESS_HOME`。

## 启动任务（主 agent，任务分配后的第一个动作）

1. 粗估 3–8 个阶段、每步 5–15 分钟粒度；每步写清 `owner`、`size`、`acceptance`、`dependsOn`。
   把计划写入临时文件 `plan.v1.json`：

   ```json
   {
     "title": "给 wordcount 加 JSON 输出",
     "goal": "支持 --json 并补齐测试，全量测试通过",
     "phases": [{"id": "p1", "title": "调研"}, {"id": "p2", "title": "实现"}],
     "agents": [
       {"id": "lead", "name": "lead", "role": "主控"},
       {"id": "coder", "name": "coder", "role": "编程", "color": "#3ddc97"}
     ],
     "steps": [
       {"id": "s1", "phaseId": "p1", "title": "读现有代码", "owner": "lead", "size": "S", "acceptance": "列出改动点"},
       {"id": "s2", "phaseId": "p2", "title": "实现 --json", "owner": "coder", "size": "M", "acceptance": "输出合法 JSON", "dependsOn": ["s1"]}
     ]
   }
   ```

2. 创建运行并注册项目：

   ```bash
   $BOARD init --project-id my-project --name "我的项目" --plan-file plan.v1.json
   ```

   输出 `run: <runId>` 与看板 URL。把 URL 放到第一条进度回执里给用户。

3. 启动 hub（若未运行）：

   ```bash
   $BOARD serve --port 8770 --open
   ```

   用后台任务方式启动，保持运行；URL 形如 `http://127.0.0.1:8770/`。
   用户打开一次即可，之后页面自动刷新。

## 执行期协议（每个 agent 都要遵守）

```bash
# 开始一步
$BOARD start s3 --agent coder
# 长时间步骤：每 60–90 秒或每个工具边界写一次心跳
$BOARD heartbeat --agent coder --step s3 --current "正在补 test_json 用例"
# 完成（必须带证据；可链式开始下一步并指定接手人）
$BOARD done s3 --agent coder --evidence tests/test_json.py --note "3 个用例通过" --start s6 --next-agent coder
# 卡住 / 失败 / 跳过 / 恢复
$BOARD block s4 --agent reviewer --reason "等待接口冻结"
$BOARD fail s4 --agent reviewer --reason "发现阻塞性缺陷"
$BOARD skip s4 --agent lead --reason "范围调整"
$BOARD resume s4 --agent reviewer
```

**长命令 / 后台任务：用 `exec` 自动记账**（不要手写 start + 轮询）：

```bash
$BOARD exec s5 --agent bg-1 --heartbeat 30 --timeout 1800 -- pytest -q
```

它自己写 `start`、每 30s 写心跳（带最后一行输出）、退出码 0 写 `done`（日志作证据）、
非 0 写 `fail`、超时杀进程组；输出实时打印，`--quiet` 可静默。用 DSH 后台任务跑它也可以，
后台面板看 raw job、看板看步骤，两边都不断更。

规则：

1. **一步一 owner**：同一时间只做一个 step；只有 owner（或 lead）能更新该步。
2. **允许并行**：无依赖的步骤可以同时 `in_progress`；依赖未完成的步骤会被看板标成 `blockedBy`。
3. **不伪造进度**：心跳只反映真实动作；长命令起后台 job，用 `job_output` 有界轮询（单次 ≤60s），
   每轮写心跳。禁止一次 `wait` 十分钟不更新。
4. **证据**：`done` 至少带一个 `--evidence`（文件、日志、测试输出路径）。
5. **失败不掩盖**：`fail` 是终态；修复要新增一步，不能把 failed 改成 done。
6. **子 agent**：只追加自己的事件，不修改 `plan.json`；需要改计划 → 发消息给 Lead。
   派生子 agent 时，把下面这段放进 spawn prompt，并给出它的 step id：

   ```
   本任务使用 live-progress 记账。你的步骤是 <stepId>（owner=<agentName>）。
   开始：$BOARD start <stepId> --agent <agentName>
   长命令/后台任务：$BOARD exec <stepId> --agent <agentName> --heartbeat 30 -- <command...>
   短步骤心跳：$BOARD heartbeat --agent <agentName> --step <stepId> --current "<在做什么>"
   完成：$BOARD done <stepId> --agent <agentName> --evidence <path> --note "<结果>"
   失败：$BOARD fail <stepId> --agent <agentName> --reason "<原因>"
   只追加事件，不修改 plan.json；计划要变就发消息给 Lead。
   ```

7. **计划变更**：Lead 用 `revise` 提交完整新计划并说明原因；被取消的步骤会自动标为
   `superseded` 保留历史，不删除、不复用 id。

   ```bash
   $BOARD revise --plan-file plan.v2.json --reason "用户追加 CSV 需求" --by lead
   ```

8. **收尾**：所有步骤终态后 `$BOARD close --by lead`；最终回复里给出
   `BOARD.md` 路径与一句汇总，必要时 `present` 它。

## 查询与排障

```bash
$BOARD status                 # 人读摘要
$BOARD --json status          # 机器读（当前快照）
$BOARD status --all           # 所有 run
$BOARD render --all           # 重建 state.json / BOARD.md
```

- 看板“最后更新 N 分钟前”变黄/红：确认对应 agent 是否还在跑；必要时 `board.py status` 复查。
- 服务挂了：数据不受影响，重新 `serve` 即可；单 run 的 `BOARD.md` 始终可读。
- 端口被占：`serve` 会自动尝试后续端口，打印实际 URL。
- 计划文件写错：`revise` 会校验并报错，不会破坏旧计划。

## 远程执行

本地 hub 是聚合器。服务器上的任务有两种接法：

1. **推送到本地**（推荐，跨 NAT 也可行，传输由调用方负责）：

   ```bash
   # 本地 hub 上登记 ingest 项目，得到 token
   $BOARD project add --id shop-api --name "商城 API" --kind ingest
   # 服务器上每次事件后推送（token 也可用 --token / DSH_PROGRESS_TOKEN）
   $BOARD push --to http://127.0.0.1:8770 --project-id shop-api --token <token>
   ```

   也可直接向 `POST /api/ingest` 发送 `{project, run, plan, events, token}`；
   事件按 `uuid` 幂等，网络重试安全。契约见 `docs/contract.md`。

2. **隧道拉取**：服务器 `serve` 绑本地回环，本地 `ssh -L 8770:127.0.0.1:8770 server`，
   浏览器访问本地 8770。零公网暴露。

安全：默认只绑 `127.0.0.1`；非回环必须 `--allow-remote`；不要把含密钥的内容写进任务备注。

## 多项目

所有已注册项目都出现在总览页 `/`；每个项目的 run 历史在 `/p/<projectId>`。
项目 id 使用显式稳定 slug，远程推送必须带上；同名冲突用不同 slug 区分。
