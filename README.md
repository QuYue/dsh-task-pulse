# live-progress

**给 DSH 多 agent 任务用的实时进度：一个网页看板，加一张输入框上方的原生卡片。**

文件是唯一事实源：主 agent 维护带版本号的计划，每个 agent 往自己的事件文件追加事实；本地 hub 把
它们渲染成实时页面，客户端插件再把当前请求的进度显示在 DSH 输入框上方。

```
项目 = 一个 DSH Session
└── 任务 = 你的一次请求（任务名 = HH:MM · 标题）
    └── 步骤 = 任务拆分（可并行、可带 0–100% 进度、可依赖）
```

默认不主动给每个任务建看板：只有用户要求实时监管，或任务本身需要（多步 / 长时 / 多 agent /
后台任务 / 远程执行）时才使用。

## 两个视图

| | 网页看板（8770） | DSH 卡片 |
|---|---|---|
| 范围 | 所有会话、所有任务 | 当前 session 的最新任务 |
| 内容 | 会话 → 任务列表 → 任务进度表、事件流、计划变更、通知 | 只放任务进度表 |
| 交互 | 删除任务/项目、步骤↔事件互跳、进度位置切换 | 折叠/展开、`注`、打开网页 |
| 用途 | 项目驾驶舱、复盘 | 抬头即见的实时进度 |

## 特性

### 网页看板

- 会话列表 → 任务列表 → 任务进度表；
- 任务进度表：状态 / 步骤 / 执行者 / 开始时间 / 结束时间 / 耗时 / 依赖阻塞 / 证据；
- 并行步骤、步骤级进度条、北京时间、`注` 备注、可选证据；
- 步骤 ↔ 事件流双向跳转；
- 所有 agent 的泳道（谁在做什么、卡在哪一步）；
- 任务删除、项目删除（可选删除磁盘数据）；
- 任务完成 / 失败 / 阻塞 / 计划升版 / 停滞通知；
- SSE 实时刷新，后台静默等待不阻塞页面。

### DSH 卡片

- 位置：`conversation.input.dock`，composer 输入框上方；
- 只显示当前 session 的**最近一次请求**对应的任务；
- 生命周期：下一次提问后隐藏，新请求创建任务后重新显示；
- 折叠态：任务名、状态、任务级进度条/百分比/完成数；
- 并行进行中的步骤各占一行：状态胶囊 + 绿色步骤条 + 步骤名；
- 展开态：`状态 | 步骤（#N + 内嵌进度条 + 标题） | 执行者 | 开始/结束 | 耗时`；
- 不显示 S/M/L 规模，不显示证据列；备注用 `注` 展开；
- 超过 10 个步骤时表格区域滚动；
- 折叠状态按 session 持久化到 localStorage；
- 与原生 Todo 同插槽共存（Todo order 0，卡片 order 1），不修改 `todos`；
- 版式：与原生 Todo/正文列同宽、20px 圆角、无外边框、输入框同色背景；
- 「打开完整看板 8770」跳到任务页；
- 与网页版并存，不替代。

折叠态示意：

```
● 18:40 · 步骤表内联进度          进行  ▓▓▓░░ 40% · 2/5   ▾
  ● 进行  ▓▓░░ 45%  #2 生成数据
  ● 进行  ▓░░░ 30%  #4 补充文档
```

展开态示意：

```
状态 | 步骤                             | 执行者 | 开始/结束         | 耗时
完成 | #1 读取配置                       | lead   | 18:40:12–18:44:03 | 3m51s
进行 | #2 ▓▓░░ 60% 生成数据              | worker | 18:44:03–         | 8m
等待 | #3 校验结果                       | worker | —                 | —
```

## 快速开始

### 1）安装 skill

```bash
# 项目级（只对当前项目生效）
mkdir -p .dsh/skills
ln -s "$PWD/live-progress/skill" .dsh/skills/live-progress

# 或用户级（所有项目生效）
ln -s "$PWD/live-progress/skill" ~/.dsh/skills/live-progress
```

DSH 会自动发现并热加载。

### 2）启动看板

```bash
python3 skill/scripts/board.py ensure
# 打开 http://127.0.0.1:8770/
```

`ensure` 会在 hub 未运行时后台拉起；`serve --port 8770 --open` 可手动前台启动。

### 3）跑演示

```bash
python3 demo/run_demo.py --open
```

演示包含两个会话：本地会话两个任务（并行 agent、后台任务、计划变更）和远程会话（ingest 推送）。

### 4）安装 DSH 卡片（可选）

```bash
cd plugin
./install.sh            # 默认 desktop profile
# 或 ./install.sh <profile>
```

Desktop profile 由 Electron 独占，脚本使用“symlink + `cordis.patch.yml` 的 `- insert:` 条目”
安装；安装后**重启 DSH Desktop**。详见 [docs/b4-install.md](docs/b4-install.md)。

卸载：

```bash
rm ~/.dsh/profiles/desktop/node_modules/dsh-live-progress-card
# 从 cordis.patch.yml 删除 dsh-live-progress-card 的 insert 条目
```

## `/live-progress` 一键启动

用户发 `/live-progress` 时，agent 先执行：

```bash
B="python3 .dsh/skills/live-progress/scripts/board.py"
$B ensure
$B auto --title "当前请求"          # ensure + 新建任务 + start 占位步骤
# 或复用当前 session 最新的 running 任务
$B auto --title "当前请求" --reuse
```

`auto` 会创建一个只有一步的占位任务，让卡片立即可见；随后用 `revise` 换成真实计划。
注意：`/live-progress` 本身只是加载 skill 指令，真正记账靠这些显式命令。

## Agent 协议

完整协议见 [skill/SKILL.md](skill/SKILL.md)；子 agent / 后台命令看
[references/record.md](skill/references/record.md)。

```bash
B="python3 skill/scripts/board.py"

# 创建任务
$B init --plan-file plan.json

# 执行
$B start s1 --agent lead
$B report s1 --percent 60 --agent lead --current "处理中"
$B done s1 --agent lead --evidence out.log --note "结果"

# 长命令 / 后台任务：自动 start → 心跳 → done/fail
$B exec s2 --agent bg-1 --heartbeat 30 --timeout 1800 -- pytest -q

# 计划变更（Lead 专用）
$B revise --plan-file plan.v2.json --reason "需求变更"

# 收尾
$B close --by lead
```

计划示例：

```json
{
  "title": "给 wordcount 加 JSON 输出",
  "goal": "支持 --json 并补齐测试，全量测试通过",
  "phases": [{"id": "p1", "title": "调研"}, {"id": "p2", "title": "实现"}],
  "agents": [
    {"id": "lead", "name": "lead", "role": "主控"},
    {"id": "coder", "name": "coder", "role": "编程", "color": "#3ddc97"}
  ],
  "steps": [
    {"id": "s1", "phaseId": "p1", "title": "读现有代码", "owner": "lead", "size": "S",
     "acceptance": "列出改动点", "order": 10},
    {"id": "s2", "phaseId": "p2", "title": "实现 --json", "owner": "coder", "size": "M",
     "acceptance": "输出合法 JSON", "order": 20, "dependsOn": ["s1"]}
  ]
}
```

步骤的 `id` 是稳定内部主键（`s1`、`s7`…），命令和事件都用它；
看板/卡片显示的是 `#1..#N` 展示序号，由 `order` 决定，可随 `revise` 变化。
两者不要互推。

## 数据布局

```
<root>/sessions/<sessionId>/tasks/<taskId>/
├── plan.json            # Lead 维护，revision 递增
├── events/<agent>.jsonl # 各 agent 只追加自己的事件
├── state.json           # 由 plan + events 推导的只读快照
└── BOARD.md             # 人读摘要
```

- 默认 root：`<cwd>/.dsh/progress`
- hub 注册表：`~/.dsh/progress/projects.json`
- 远程镜像：`~/.dsh/progress/inbox/<sessionId>/tasks/`
- 沙箱只允许工作区写入时，hub 回退到 `<cwd>/.dsh/progress/hub`

接口契约见 [docs/contract.md](docs/contract.md)。

## 远程执行

1. **推送到本地**（跨 NAT 可行，传输由调用方负责）：

```bash
$B project add --id shop-api --kind ingest
$B push --to http://127.0.0.1:8770 --project-id shop-api --token <token>
```

也可直接 `POST /api/ingest`，token 校验、事件 `uuid` 幂等。

2. **SSH 隧道**：服务器 `serve` 绑回环，本地 `ssh -L 8770:127.0.0.1:8770 server`。

默认只监听 `127.0.0.1`；非回环需 `--allow-remote`。

## 命令速查

```bash
$B ensure [--port 8770]                 # hub 没开就后台拉起
$B auto --title "..." [--reuse]         # ensure + 新任务/复用 running 任务
$B init --plan-file plan.json           # 创建任务
$B start/done/block/fail/skip/resume ... # 步骤状态
$B heartbeat --agent ... --step ...     # 心跳
$B report --percent 60 --agent ...      # 步骤进度
$B exec ... -- <command>                # 长命令自动记账
$B revise --plan-file plan.v2.json      # 计划变更
$B status [--json] [--all]              # 查询
$B render --all                         # 重建 state/BOARD
$B close --by lead                      # 收尾
$B prune --keep 20 [--dry-run]          # 清理旧任务
$B serve --port 8770 [--open]           # 手动起 hub
$B project add/push ...                 # 远程
```

## 测试

```bash
python3 -m unittest discover -s tests -v
node plugin/smoke-test.cjs
```

当前：33 个后端测试 + 卡片 bundle 冒烟测试。

## 版本与发布

- **v2.0.3（当前）**：与原生 Todo/正文列同宽、20px 圆角、无外边框、输入框同色背景；
  重写 README，新增排障文档与 v2 最终规格；
- **v2.0.2**：展开表无 S/M/L、`#N` 后内嵌进度条、composer 同宽同背景；
- **v2.0.1**：卡片对齐修复、安装 `- insert:` 修复、`ensure`/`auto`；
- **v2.0.0**：DSH 输入框上方卡片首版；
- **v1.0.0**：网页看板 + 文件驱动账本。

发布记录见 [CHANGELOG.md](CHANGELOG.md)；
v2 规格见 [docs/v2-card-spec.md](docs/v2-card-spec.md)，
排障见 [docs/troubleshooting.md](docs/troubleshooting.md)，
B0 插槽结论见 [docs/v2-b0-findings.md](docs/v2-b0-findings.md)。

## 已知限制

- DSH 客户端 slot API 未承诺长期稳定，升级 DSH 后需回归卡片；
- 安装卡片后需要重启 DSH Desktop 才加载 client bundle；
- `/live-progress` 不会自动记账，必须由 agent 执行 `ensure`/`auto`/`start` 等命令；
- 卡片只显示最近一次请求的任务，下一次提问后隐藏是设计行为；
- `auto` 创建的是占位任务，真实步骤需要 `revise`。

## 设计取舍

- **文件是唯一事实源**：hub 可挂、可换、可重启，文件永远可审计、可回放；
- **事件按 agent 分文件**：多 agent 并行追加零锁冲突；
- **计划与事件分离**：改范围是 Lead 的决策，执行事实是各 agent 的产出；
- **页面只读快照**：模型不用为刷新消耗 token；
- **展示序号与内部 id 分离**：`#N` 随真实顺序变，`sN` 稳定供事件/命令使用。
