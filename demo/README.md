# live-progress demo

按 v3 模型演示：**项目 = DSH Session，任务 = 一次请求，步骤 = 任务拆分**。

| 会话（项目） | 内容 |
|---|---|
| `demo-session` | 同一会话里两个任务：① wordcount 加 JSON/CSV（并行 agent、后台 exec 测试、计划 v2）② 修 README（短任务） |
| `demo-remote-session` | 模拟服务器会话，通过 token 把任务/事件 POST 到本地 hub（`/api/ingest`） |

## 运行

```bash
python3 demo/run_demo.py --open        # 正常速度约 50 秒
python3 demo/run_demo.py --fast        # 约 18 秒
python3 demo/run_demo.py --fresh       # 清掉上次 demo 数据
```

脚本默认在 `127.0.0.1:8770` 启动 hub，结束后保持运行（Ctrl+C 退出）；若已有服务则复用。

## 你会看到

1. 总览页出现 3 个会话：当前 DSH 会话（含迁移过来的 P0 任务）、`demo-session`、`demo-remote-session`；
2. 进入 `demo-session`，任务列表有 2 个任务，名字形如 `17:43 · wordcount 增加 JSON 输出`；
3. 点任务进入「任务进度表」：
   - 步骤完成/进行中/待开始一眼可见，待开始的步骤**不显示执行者**；
   - 进行中的步骤有独立进度条（`report`/`exec` 上报，例如 45%）；
   - coder 与 reviewer 两条泳道并行，后台 `bg-1` 由 `exec` 自动记录 start/进度/完成；
   - 中途计划从 v1 升到 v2（新增 CSV 步骤），旧历史保留；
4. 顶部「全部任务」已移除——任务按会话归档；总览只列会话；
5. 完成/失败/阻塞/升版会触发通知（页面打开时用浏览器通知）。

## 数据位置

- 本地会话：`demo/demo_a/.dsh/progress/sessions/demo-session/tasks/`
- 远程镜像：`demo/.hub/inbox/demo-remote-session/tasks/`
- 都在 `.gitignore` 中。

## 说明

演示里的“写代码/审查/测试”是脚本模拟步骤，不会改动 `demo_a/task/` 的示例项目；
产物写在 `demo/demo_a/artifacts/`，作为步骤证据。
