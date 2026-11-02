# TaskPulse

**DSH 的实时任务进度：一个共享看板，加一张输入框上方的原生卡片，再加一个 `/tp` 原生命令。**

TaskPulse 把“任务在做什么、做到哪、谁在做”变成 DSH 里随时可见的状态：

```
Session（DSH 会话 / 工作区）
└── Project（一个 session 下可以有多个逻辑项目）
    └── Task（一次请求）
        └── Step（可并行、带进度、可依赖）
```

文件是唯一事实源：主 agent 维护版本化计划，所有 agent 追加事件；本地 hub（8770）把它们渲染成
实时网页，插件把当前任务显示在 composer 上方。

## 两个视图 + 一个原生命令

| | 网页看板（8770） | DSH 卡片 |
|---|---|---|
| 范围 | 所有会话、所有任务 | 当前 session 的最新任务 |
| 内容 | 会话 → 任务列表 → 任务进度表、事件流、计划变更 | 只放任务进度表 |
| 交互 | 删除任务/项目、步骤↔事件互跳、进度位置切换 | 折叠/展开、`注`、打开网页 |

原生 `/tp` 命令直接在 Host 侧执行，不经过模型：

```text
/tp server start
/tp server stop
/tp server status
/tp project new [名称]
/tp project use <名称>
/tp project rename "新名称"
/tp project list
/tp task new ["标题"] [内容...]
/tp task update ["标题"] [内容...]
/tp task auto ["标题"] [内容...]
/tp task list
/tp help
```

## 特性

### 网页看板

- 会话列表 → 任务列表 → 任务进度表；
- 状态 / 步骤 / 执行者 / 开始时间 / 结束时间 / 耗时 / 依赖阻塞 / 证据；
- 并行步骤、步骤级进度条、北京时间、`注` 备注、可选证据；
- 步骤 ↔ 事件流双向跳转；
- 所有 agent 的泳道；
- 任务/项目删除（项目可选删除磁盘数据）；
- 完成 / 失败 / 阻塞 / 计划升版 / 停滞通知；
- SSE 实时刷新。

### DSH 卡片

- 位置：`conversation.input.dock`，composer 输入框上方；
- 只显示当前 session 的最近任务；
- 折叠态：任务名、状态、任务级进度条/百分比/完成数；
- 并行进行中的步骤各占一行：状态胶囊 + 绿色步骤条 + 步骤名；
- 展开态：`状态 | 步骤（#N + 内嵌进度条 + 标题） | 执行者 | 开始/结束 | 耗时`；
- 不显示 S/M/L、不显示证据列；`注` 展开备注；>10 步滚动；
- 与原生 Todo 同插槽共存（Todo order 0，卡片 order 1）；
- 与 TaskPulse 共享 hub 自动发现（优先 8770，兜底 8770–8789）。

## 安装

### 单包安装（推荐）

```bash
git clone https://github.com/QuYue/dsh-task-pulse.git
cd dsh-task-pulse
./install.sh desktop
```

脚本会：

1. 在 `~/.dsh/profiles/desktop/node_modules/@quyue/dsh-task-pulse` 建立到本仓库的 symlink；
2. 在 `cordis.patch.yml` 追加 loader 条目：

```yaml
- insert:
    - id: task-pulse
      name: "@quyue/dsh-task-pulse"
```

安装后**重启 DSH Desktop**。不再需要 `~/.dsh/skills/live-progress` symlink——skill 由插件
通过官方 provider 注册。

卸载：

```bash
rm ~/.dsh/profiles/desktop/node_modules/@quyue/dsh-task-pulse
# 从 cordis.patch.yml 删除 task-pulse 的 insert 条目
```

## 使用

### 用户

```text
/task-pulse                     # skill 入口：ensure 8770，模型判断 new/update
/tp server status               # 原生命令：查看服务与当前任务
/tp project new "LOT v7"         # 新建逻辑项目并切换过去
/tp project use "LOT v7"         # 切换当前项目
/tp project list                 # 项目列表
/tp task new "LOT v7 统计" 统计 2024 年各层数量  # 在 current project 新建任务并唤醒模型
/tp task update 补充要求          # 继续当前任务，不新建
/tp task auto "当前请求" 内容     # 有 running 当前任务则继续，否则新建
```

### Agent / 脚本

skill 正文末尾会注入 `BOARD` 与 `ASSETS` 的绝对路径；也可以直接：

```bash
BOARD="python3 /path/to/dsh-task-pulse/assets/task-pulse/scripts/board.py"

$BOARD ensure
$BOARD auto --title "当前请求"
$BOARD status
$BOARD start s1 --agent lead
$BOARD report s1 --percent 60 --agent lead
$BOARD done s1 --agent lead --evidence out.log
$BOARD exec s2 --agent bg-1 --heartbeat 30 -- pytest -q
$BOARD revise --plan-file plan.v2.json --reason "需求变更"
$BOARD close --by lead
```

## 数据布局

```text
<root>/sessions/<sessionId>/
├── current_project.json
└── projects/<projectId>/
    ├── project.json
    ├── current_task.json
    └── tasks/<taskId>/
        ├── plan.json
        ├── events/<agent>.jsonl
        ├── state.json
        └── BOARD.md
```

默认 root：`<cwd>/.dsh/progress`。  
共享 hub：`http://127.0.0.1:8770/`；多个项目通过 `POST /api/project/register` 注册到同一个 hub。

旧 live-progress 数据目录结构兼容：首次使用 project 层时，旧的 `sessions/<sid>/tasks/` 会自动迁移到
`projects/default/tasks/`。root 固定在工作区 `.dsh/progress`，不再放在 repo 目录里。

## 开发与 npm 规范

```bash
python3 -m unittest discover -s tests -v
node tests/smoke-test.cjs
npm pack --dry-run
```

包名：`@quyue/dsh-task-pulse`；技能名：`task-pulse`；命令：`/tp`。  
当前暂不发布 npm，但 `package.json` 已按 npm 规范准备（`files`、`exports`、`peerDependencies`、
`publishConfig`、LICENSE）。

## 从 live-progress 迁移

- 包名：`dsh-live-progress-card` → `@quyue/dsh-task-pulse`；
- skill：`/live-progress` → `/task-pulse`；
- 命令：`/lp` 不再使用，改用 `/tp`；
- 单包结构：`skill/` + `plugin/` → `assets/task-pulse/` + `lib/` + 根 `package.json`；
- 数据 schema 和 8770 看板 URL 不变；
- 旧 profile symlink / patch 条目需要移除，重新运行 `./install.sh`。

## Project 层

- 一个 DSH session 可以包含多个逻辑 project；
- `/tp project new|use|rename|list` 管理 current project；
- `/tp task *` 全部作用于 current project；
- 旧任务自动进入 `default` project；
- 看板任务列表会显示所属 project 名称；
- project/task 的网页重命名 UI 还在后续版本。

## License

MIT
