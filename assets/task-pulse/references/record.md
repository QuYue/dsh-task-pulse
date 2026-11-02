# 最小记账协议（给子 agent / 后台命令 / 被包装的程序）

> 只对 Lead 已经 `init` 的任务使用；不要自己创建任务，也不要给每个请求都记账。

你只需要 3 条命令 + 1 个包装器。**不要修改 `plan.json`，不要管看板怎么渲染。**

```bash
BOARD="python3 <插件注入的 BOARD 路径>"
# BOARD / ASSETS 的绝对路径由 TaskPulse skill provider 注入；也可以指向仓库 assets/task-pulse/scripts/board.py。
```

## 0. 上下文（自动带入）

- Session = 当前 DSH 工作区；一个 session 下可以有多个逻辑 project。
- 默认记账到 current project，不用你指定 project id。
- 任务 = 当前这次请求；任务名自动是 `HH:MM · 计划标题`。
- 你的步骤 id 由 Lead 分配；失败重试会开新任务。

## 1. 开始 / 完成 / 失败

```bash
$BOARD start s3 --agent coder
$BOARD done s3 --agent coder --evidence reports/out.md --note "结果摘要"
$BOARD fail s3 --agent coder --reason "具体失败原因"
$BOARD block s3 --agent coder --reason "在等什么"
$BOARD resume s3 --agent coder
```

- 一次只做一个 step；只有该 step 的 owner（或 lead）能改它。
- `--evidence`（文件/日志/测试输出/URL）和 `--note` 都是可选的；没有产物就不写，不影响完成。
- 失败是终态：修复要新增一步，不要把 failed 改成 done。

## 2. 长命令 / 后台任务：用 `exec` 自动记账

```bash
$BOARD exec s5 --agent bg-1 --heartbeat 30 --timeout 1800 -- pytest -q
```

它会：

1. 自动写 `start`；
2. 每 `--heartbeat` 秒写一次心跳（带最后一行输出），看板始终是活的；
3. 退出码 0 → `done`（日志作为 evidence）；非 0 → `fail`；
4. `--timeout` 到点杀进程组并记 `fail(timeout)`；
5. 输出实时打印到终端（`--quiet` 可关闭），完整日志落在 run 的 `exec/` 下。

用 DSH 后台任务跑 `exec` 也可以：后台任务面板看原始 job，看板看步骤进度，两边都不断更。
**不要再采用“起前台命令然后 job_output 干等十分钟”的模式。**

## 3. 心跳

继续已有任务或同一个 step 前，先写一次 heartbeat 刷新活跃时间；没有用 `exec` 的短步骤，在工具边界用：

```bash
$BOARD heartbeat --agent coder --step s3 --current "正在写 test_json 用例"
```

## 4. 步骤进度

```bash
$BOARD report s3 --percent 45 --agent coder --current "读取数据 45%"
```

- `--percent` 0–100，只更新进度，不改状态；done 时自动 100%。
- 用 `exec` 时子进程会拿到 `LIVE_PROGRESS_*` 环境变量，可以直接调用：
  `$LIVE_PROGRESS_PYTHON $LIVE_PROGRESS_BOARD report ...`。
- `exec` 也会把子进程输出中 `progress: 40` 这样的行自动转成进度。

## 5. spawn 模板（Lead 复制给子 agent）

```
本任务使用 task-pulse 记账。你的步骤是 <stepId>（owner=<agentName>）。
开始：$BOARD start <stepId> --agent <agentName>
长命令/后台任务：$BOARD exec <stepId> --agent <agentName> --heartbeat 30 -- <command...>
短步骤心跳：$BOARD heartbeat --agent <agentName> --step <stepId> --current "<在做什么>"
完成：$BOARD done <stepId> --agent <agentName> --evidence <path> --note "<结果>"
失败：$BOARD fail <stepId> --agent <agentName> --reason "<原因>"
只写你自己的事件，不修改 plan.json；计划要变就发消息给 Lead。
```

## 6. 三条红线

1. 不伪造进度：心跳只反映真实动作。
2. 不碰别人的 step，不改计划；计划变更找 Lead。
3. 收尾前确认自己的 step 都有终态（done / failed / blocked 都要有说明）。
