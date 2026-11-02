## live-progress

多步任务、派生子 agent 或启动后台任务时，加载 `live-progress` skill 并记账：

- Lead：`board.py init` 建计划、`revise` 改计划、`close` 收尾；
- 子 agent / 后台命令：`board.py start / heartbeat / done / fail`，长命令用 `board.py exec` 自动记账；
- 不修改 `plan.json`；计划变更交给 Lead。

脚本路径：`.dsh/skills/live-progress/scripts/board.py`（或 `~/.dsh/skills/live-progress/scripts/board.py`）。
协议细节：该 skill 的 `SKILL.md` 与 `references/record.md`。
