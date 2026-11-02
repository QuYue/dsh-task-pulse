# Changelog

## v1.0.0 — 2026-11-02

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
