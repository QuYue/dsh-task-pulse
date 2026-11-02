# Changelog

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
