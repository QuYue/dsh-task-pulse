## TaskPulse

当用户要求实时进度，或任务本身需要（多步/长时间/多 agent/后台/远程）时，再加载 `task-pulse` 并记账；普通任务不要用。

- 继续已有任务：先 `board.py status`，再 `start`；`/task-pulse` 只加载指令，不自动记账；
- Lead：`board.py init` 建计划、`revise` 改计划、`close` 收尾；
- 子 agent / 后台命令：`board.py start / heartbeat / done / fail`，长命令用 `board.py exec` 自动记账；
- 不修改 `plan.json`；计划变更交给 Lead。

脚本路径由插件 skill provider 注入（`BOARD` / `ASSETS` 绝对路径）。
协议细节：该 skill 的 `SKILL.md` 与 `references/record.md`。
