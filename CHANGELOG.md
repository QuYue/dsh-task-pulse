# Changelog

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
