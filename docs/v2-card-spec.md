# v1 基线 & v2 卡片版规格

本文记录 live-progress 的版本划分，以及 v2（DSH 内卡片）定稿的产品逻辑。
v1 = 网页看板版本；v2 = 在 DSH 输入框上方增加原生进度卡片。

## v1（网页看板基线）

- 文件是唯一事实源：`sessions/<sessionId>/tasks/<taskId>/`（plan + events）
- 项目 = DSH Session；任务 = 一次用户请求；步骤 = 任务拆分
- 网页看板（8770）：会话列表 → 任务列表 → 任务进度表
- 步骤支持：并行、进度百分比、执行者、开始/结束时间（北京时间）、耗时、
  依赖阻塞、备注（`注` 可展开）、可选证据
- 状态词：完成 / 等待 / 进行 / 失败（跳过/已取消为边缘态）
- 步骤 ↔ 事件流双向跳转；任务/项目可删除（项目可选删磁盘数据）
- 长命令/后台任务用 `board.py exec` 自动记账；远程 `ingest` 推送
- 默认不主动为每个任务建看板；用户要求或任务需要时才启用

## v2 目标

**在 DSH 内新增一个原生卡片视图，与网页版并存，不是替代。**

- 位置：composer 输入框上方的 `conversation.input.dock`（与原生 Todo list 同层）
- 范围：**只显示当前 session**
- 任务：**只显示最近一次用户提问所产生的任务**；不提供任务切换
- 生命周期：
  - 该请求创建任务后出现；
  - 任务完成后保留显示；
  - 下一次用户提问到达时隐藏（与原生 todo 一致）；
  - 新请求若创建新任务则显示新任务，否则保持隐藏；
  - 实现规则：任务的 `startedAt` 早于“最后一条用户消息”则隐藏。
- 内容：**只放任务进度表**
  - 折叠态（第一行）：任务名 + 状态 + **任务级进度条** + 百分比 + `done/total` + 展开按钮
  - 折叠态（第二行起）：**每个进行中的步骤一行**（并行时多行），每行：
    状态小胶囊（与任务进度表一致的「进行」样式）+ 绿色步骤进度条 + 百分比 + 步骤名；
    不显示「正在：」字样；无进行中步骤时显示「等待下一步」
  - 顺序：**40% 在前，2/5 在后**
  - 展开态：状态 | 步骤（`#N` + 进度条/百分比 + 标题，不显示 S/M/L） | 执行者 | 开始/结束时间 | 耗时；
    进度条与网页版一样内嵌在步骤单元格，紧跟 `#N` 后面
  - 不显示证据列；备注用 `注` 图标，点击展开
  - 不显示事件流、计划变更、项目列表
  - 展开后步骤超过 10 条时，步骤表在固定高度内滚动（max-height 300px），页面不被拉长
  - `[打开完整看板]` 打开 8770 任务页

## 最终样式（v2.0.3）

- 宽度：与原生 Todo / 正文列同宽，使用 TodoPanel 公式：
  `width: calc(100% - 2*side-clearance - 4*dock-inset)`，
  `max-width: calc(composer-card-max-width - 4*dock-inset)`，`margin: 0 auto`；
- 圆角：`var(--dsw-radius-xl, 20px)`；
- 无外边框；背景使用输入框的 `var(--dsw-specific-input-major)`；
- 内容与交互：
  - 折叠栏：`任务名 + 状态 + 任务级进度条 + 百分比 + done/total`；
  - 并行步骤：每行状态胶囊 + 绿色步骤条 + `#N 步骤名`；
  - 展开表：5 列（状态/步骤/执行者/开始结束/耗时），无 S/M/L、无证据列；
  - `注` 点击展开；折叠状态按 session 持久化到 localStorage；
- 与原生 Todo 的关系：
  - 同一个 `conversation.input.dock`，原生 Todo `id=todo, order=0`，卡片 `id=live-progress-card, order=1`；
  - 不改 `todos` projection，不调用 `todo_write`，两者可同时显示；
  - 原生 Todo 由浏览器/会话状态持久化，卡片依赖 hub 与生命周期。

## 技术路线

- DSH 客户端插件（`dsh.client` bundle），注册到 `conversation.input.dock`；
- 插件装进 Desktop profile（`~/.dsh/profiles/desktop`）；
- 安装方式：profile `node_modules` 本地 symlink + `cordis.patch.yml` 的 `- insert:` 条目；
- hub 增加只读 CORS，供插件读取 `/api/state`；插件每 1.5s 轮询；
- 不修改 DSH 本体。

## 阶段

| 阶段 | 内容 | 状态 |
|---|---|---|
| B0 | 验证 dock 插槽可被第三方插件注册、安装路径可行 | ✅ |
| B1 | 插件骨架 + 静态卡片（折叠/展开） | ✅ |
| B2 | 接 hub 实时数据 + “当前请求任务”生命周期 | ✅ |
| B3 | `注` 展开、打开 8770、折叠状态持久化 | ✅ |
| B4 | 安装脚本、版本兼容说明、发布 | ✅ v2.0.3 |

## 边界与排障

- 卡片是轻量附加视图，不取代网页看板；
- 不影响原生 Todo dock；两者可同时存在；
- 普通问答/未启用 live-progress 的请求不会出现卡片；
- 修改 client bundle 后必须重启 DSH Desktop 才会加载；
- DSH 重启可能带走 hub：先 `board.py ensure`；
- 旧任务在下一次提问后隐藏是设计行为；需要显示当前请求时用 `auto` 建任务；
- 插件升级跟随 DSH 客户端 API；升级 DSH 后需回归验证。

详见 [troubleshooting.md](troubleshooting.md)。
