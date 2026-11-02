# P0 dogfood 报告（2026-11-02）

用 live-progress 自身跑了一次真实多 agent 任务：给 `board.py` 增加 `prune` 命令。
目的是验证「agent / 后台 / 程序记账」是否真的能落下来，而不是验证代码功能。

## 运行

- 项目：`live-progress-v12`，run `20261102-170326-a6a3`
- 看板：`http://127.0.0.1:8770/r/live-progress-v12/20261102-170326-a6a3`
- 计划：6 步，Lead 2 步、队友 p0-dev 2 步、后台 bg-1 1 步、Lead 文档/复核 2 步

## 记账结果

| 步骤 | 执行者 | 记账方式 | 结果 |
|---|---|---|---|
| s1 定语义 | Lead | 手动 start/done | ✅ |
| s2 实现 prune | p0-dev | start + 2 次心跳 + done | ✅ |
| s3 补测试 | p0-dev | start + 1 次心跳 + done | ✅ |
| s4 跑全量测试 | bg-1 | `board.py exec` 自动 start/done | ✅（7s，短于心跳间隔，无心跳符合预期） |
| s5 文档 | Lead | 手动 start/done | ✅ |
| s6 复核关闭 | Lead | 手动 start/done + close | ✅ |

最终 `6/6`，没有漏记、没有残留 in_progress；`exec` 日志自动成为 s4 证据。

## 观察

1. **协议可执行**：队友按 spawn prompt + `references/record.md` 执行，未出现漏 start/漏 done；
   `AGENTS.md` 注入让会话默认知道要记账。
2. **短任务的心跳**：s4 只跑 7 秒，`--heartbeat 10` 来不及写心跳；这正常，但看板上短任务只有
   start/done。建议短命令用 `--heartbeat 3–5`，或明确接受“只有起止”。
3. **prune 与 running 的交互**：`init` 出来的 run 默认 `status=running`，`prune` 会跳过它们。
   已写进 README/contract：要清理先 `close`；先 `--dry-run` 再 `--yes`。
4. **无噪音**：本次没有触发失败/阻塞/升版，因此没有额外通知；完成时由 hub 正常发一次通知。
5. **仍待验证**：远程网络传输（目前只在本机模拟 POST）、跨机时钟偏差、长时间任务的心跳节奏。

## 结论

记账层（手动命令 + `exec` 包装 + `AGENTS.md` + record.md）在真实协作里可用。
下一步优先 P1：远程链路（服务器 → 本地 hub 的传输与断网重试），再 P2 常驻/默认化。
