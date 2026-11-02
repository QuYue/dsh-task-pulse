# Changelog

## v3.5.0 — 2026-11-03

- 卡片可见性从 `startedAt` 改为「最近活跃时间」：
  - `max(startedAt, updatedAt)` 与最后一条用户消息比较；
  - 完成后仍保留，下一次用户消息隐藏；
- `/tp task update` / `task auto` 继续任务时自动写一次 heartbeat，刷新活跃时间；
- agent 直接继续旧任务时，SKILL 要求先 heartbeat；
- smoke test 增加继续任务场景。

## v3.4.7 — 2026-11-03

- Host 插件加载时自动执行 `board.py ensure`，DSH 重启后 8770 hub 不再需要手动启动；
- 卡片和 `/tp` 仍会兜底重试/拉起。

## v3.4.6 — 2026-11-03

- 修复卡片组件在移除空项目兜底时误删 `const task = selectTask(...)` 的问题；
  该引用错误导致整个 slot entry 崩溃、卡片完全不可见；
- smoke test 增加“组件必须先计算 task”的防回归检查。

## v3.4.5 — 2026-11-03

- 修复 v2 卡片生命周期使用了错误的“最后更新时间”：
  - 之前用 session row.updatedAt，会被 assistant/tool 活动推进；
  - 现在优先使用 sessionListMetadata.lastPromptAt，只跟最后一条用户消息比较；
  - 任务创建后卡片不会再被自己的执行活动隐藏。

## v3.4.4 — 2026-11-03

- 卡片选择逻辑恢复为 v2：
  - 只看当前 session 的最新任务，不再按 current project 过滤；
  - 任务完成后保留；
  - 下一次用户消息到达时隐藏；
  - 没有任务时不显示卡片。

## v3.4.3 — 2026-11-03

- 移除“当前项目”空卡片兜底：没有可见任务时卡片直接隐藏；
- 修复 current project 有任务却显示“暂无任务”的问题：
  旧逻辑在任务被生命周期隐藏后回退到空项目卡片，且文案写死；
  现在只显示真正可展示的任务，否则不显示卡片。

## v3.4.2 — 2026-11-03

- project 页面：重命名/删除按钮移到 project 名同一行并右对齐；
- project 页面标题显示逻辑 project 名（带「逻辑项目」标记）；
- 任务列表操作列改为符号按钮：✎ 重命名、× 删除；
- 操作列加宽，避免两个按钮换行。

## v3.4.1 — 2026-11-03

- 任务详情页标题行操作调整：
  - 重命名按钮缩小；
  - 重命名/删除放在任务名同一行并右对齐；
  - 重命名按钮后新增删除按钮。

## v3.4.0 — 2026-11-03

- 网页版支持重命名：
  - 逻辑 project 卡片 ✎ → 重命名 project；
  - 任务列表「改名」→ 重命名 task；
  - 任务详情页「重命名」；
- 新增 `/api/local-project/rename` 与 `/api/task/rename`；
- 重命名只改显示名，project id / task id / 目录 / 事件历史不变。

## v3.3.3 — 2026-11-03

- 允许 agent 自己决定任务名：
  - 无引号标题时先按内容首行生成临时标题；
  - followup 明确要求 agent 用 `board.py rename --name` 改成最终名字；
- 新增 `/tp task rename "新名称"` 与 `board.py rename`；
- 重命名只改显示名，task id / 目录 / 事件不变。

## v3.3.2 — 2026-11-03

- 修正 `/tp task new|auto` 无标题时的默认名：
  - 之前固定为「当前请求」；
  - 现在取任务内容首行（最多 30 字）；
  - 无内容时使用「任务」。

## v3.3.1 — 2026-11-03

- 逻辑 project 卡片新增删除按钮（×）；
- 新增 `/api/local-project/delete` 与 `/tp project delete [名称]`；
- 删除为归档：project 目录移到 `<session>/.trash/`，不直接抹盘；
- 删除当前 project 时自动切换到剩余 project；拒绝删除最后一个 project。

## v3.3.0 — 2026-11-03

- 总览看板改为按**逻辑 project** 展开：每个 project 一张卡片，不再只显示 session；
- 空 project 也有独立卡片，显示任务数/当前标记；
- session 页保留项目筛选栏；
- 测试不再注册到共享 hub，避免 `test-session` 污染看板。

## v3.2.3 — 2026-11-03

- DSH 卡片显示当前 project：
  - 有任务时在任务名旁显示 project chip；
  - 当前 project 无任务时显示「当前项目 / 暂无任务」卡片，不再整卡消失；
- 点击空项目卡片可打开对应看板。

## v3.2.2 — 2026-11-03

- session 任务列表页新增「项目」筛选栏：`全部任务` + 每个逻辑项目；
- 空项目也有入口（显示任务数 0），支持 `/p/<session>?project=<localProjectId>`；
- 项目切换/重命名后 hub 状态会刷新。

## v3.2.1 — 2026-11-03

- 修复 `/tp` Host 使用可变 cwd 的默认 hub home，导致 8770 重启后 registry 为空；
  现在固定使用 `~/.dsh/progress` 作为共享 hub home；
- 看板 session 卡片新增逻辑项目列表（即使 0 任务也显示）；
- 当前项目无任务时卡片不再回退显示其他项目的旧任务；
- hub 状态缓存加入 current_project/project.json/current_task 变化检测。

## v3.2.0 — 2026-11-03

- Project 层：Session 下支持多个逻辑 Project；
- `/tp project new|use|rename|list`；
- `/tp task *` 作用于 current project；
- 数据布局：`sessions/<sid>/projects/<projectId>/tasks/...`，旧任务自动迁入 `default`；
- 看板任务列表显示 project 名称；卡片优先显示 current project 的任务；
- 新增 `local-project` CLI 与 project 隔离测试。

## v3.1.0 — 2026-11-03

- `/tp task new|update|auto` 支持 `标题 + 内容`：
  - `"标题" 内容...` → 标题 + 正文；
  - 没有引号时整段作为内容，标题用默认 `当前请求`；
- 内容写入占位任务的 `plan.goal`，并带入 followup prompt；
- 更新 `/tp help`、SKILL.md、README 语法说明。

## v3.0.2 — 2026-11-03

- 修复 `/tp` 命令使用 Host 进程 cwd 而不是 DSH Session cwd 的问题；
- 现在优先读取 `agent.session.header.cwd`，避免任务/数据落到 profile 目录；
- 修复后 `/tp task new` 会在当前 session 的 workspace 下创建 `.dsh/progress`。

## v3.0.1 — 2026-11-03

- 修复 sandbox 下 `~/.dsh/progress` 不可写时 `default_home()` 误返回不可写目录，
  导致 `/tp task new` 报 `.projects.lock` EPERM 的问题；
- 现在会探测可写性，失败则回退到 `<cwd>/.dsh/progress/hub`。

## v3.0.0 — 2026-11-03

TaskPulse 单包重构。

- 包名：`@quyue/dsh-task-pulse`；
- 单包：根目录同时包含 Host 插件、skill provider、`/tp` 命令、client 卡片和 board assets；
- skill：`task-pulse`，使用官方 `ctx.skills.registerProvider()` bundled provider 形态；
- 命令：`/tp`，原生命令；不再使用 `/lp` 过渡；
- 结构：`skill/` + `plugin/` → `assets/task-pulse/` + `lib/` + 根 `package.json`；
- npm 规范：`files`、`exports`、`peerDependencies`、`publishConfig`、LICENSE；
- 数据 root 迁出 repo，固定在工作区 `.dsh/progress`；共享 hub 8770；
- 卡片 bundle id / slot id / localStorage 前缀改为 TaskPulse；
- 新增 `board.py current` 与 `/api/shutdown`，支持 `/tp task update|auto` 与 `/tp server stop`；
- 测试与文档更新为 TaskPulse。

## v2.0.3 — 2026-11-03

最终样式与文档。

- 卡片宽度改为与原生 Todo / 正文列同宽（TodoPanel 公式），不再用 composer 宽度；
- 圆角改为 `var(--dsw-radius-xl, 20px)`，去掉外边框；
- 背景保持输入框的 `--dsw-specific-input-major`；
- 与原生 Todo 同 slot 共存（Todo order 0，卡片 order 1），不修改 `todos`；
- 新增 [docs/troubleshooting.md](docs/troubleshooting.md)：卡片不显示、hub、安装、共存排障；
- 更新 [docs/v2-card-spec.md](docs/v2-card-spec.md) 最终样式与阶段状态；
- README 更新 v2.0.3；
- 33 tests + smoke test 通过。

## v2.0.2 — 2026-11-03

卡片最终版与 README 重写。

- 展开表去掉 S/M/L，只显示 `#N`；
- 进度条不再单独成列，改为和步骤融合：内嵌在步骤单元格、紧跟 `#N`；
- 修复内嵌进度条 `span` 未设置 `display` 导致只显示百分比、不显示条；
- 卡片宽度直接使用 composer 的 `max-width: var(--dsh-composer-card-max-width)`，
  与输入框同宽居中；
- 背景改为输入框的 `--dsw-specific-input-major`；
- README 重写：覆盖 v1 网页看板、v2 卡片、安装、`/live-progress` 一键启动、远程、测试；
- 33 个后端测试 + 卡片 bundle 冒烟测试通过。

## v2.0.1 — 2026-11-03

首个可用版本：网页看板 + 文件驱动的进度账本。

- 项目 = DSH Session，任务 = 一次用户请求，步骤 = 任务拆分
- `board.py`：init / start / done / block / fail / skip / resume / report /
  heartbeat / revise / close / exec / status / render / prune / serve /
  project / task / migrate / push
- 网页看板：会话列表 → 任务列表 → 任务进度表；SSE 实时刷新
- 任务进度表：并行步骤、进度百分比、执行者、北京时间起止、耗时、
  依赖阻塞、备注（可展开）、可选证据、步骤↔事件流互跳
- 状态词：完成 / 等待 / 进行 / 失败
- 长命令/后台任务 `exec` 自动记账；远程 `/api/ingest`（token、幂等）
- 任务/项目删除（项目可选 purge 磁盘数据）；页面内确认弹窗
- 通知：完成 / 失败 / 阻塞 / 计划升版 / 停滞；浏览器 + 系统通知
- 默认不主动使用：用户要求或任务需要时才启用

## v2.0.1 — 2026-11-03

- 卡片宽度按 composer 的 `side-clearance` / `dock-inset` 对齐；
- 安装补丁改为 `- insert:` 语法（原先裸 Loader 条目会被 profile 拒绝）；
- 新增 `board.py ensure`：hub 未运行时后台拉起；
- 新增 `board.py auto --title ...`：ensure + 为当前请求自动建任务并 start s1，
  可 `--reuse` 复用最新 running 任务；供 `/live-progress` 一键使用；
- 验证：卡片在 DSH 中显示；B2/B3/B4 联调通过；33 tests 通过。

## v2.0.0 — 2026-11-03

DSH 输入框上方的 live-progress 卡片（与网页版并存）。

- 位置：`conversation.input.dock`（原生 Todo 同层，order 1）；
- 数据：每 1.5s 读 hub `/api/state`；只显示当前 session 最新任务；
- 生命周期：下一次提问后自动隐藏，新任务创建后显示；
- 折叠栏：任务名、状态、任务级进度条/百分比/完成数、并行进行中步骤（状态胶囊 + 绿色步骤条）；
- 展开：步骤表（状态/步骤/执行者/进度/北京时间/耗时）、`注`、>10 步滚动；
- 交互：折叠状态按 session 持久化、打开 8770 任务页；
- 安装：Desktop profile symlink + `cordis.patch.yml` 的 `- insert:` 条目；
- 已知限制：需要重启 DSH 才加载；client API 随 DSH 升级需回归。
