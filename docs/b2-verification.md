# B2 联调记录

目标：在未安装到 DSH 前，验证卡片能消费真实 hub 数据并遵守“下一次提问隐藏”的生命周期。

## 方法

- 用 jsdom 提供 DOM；
- 用轻量 React hooks 模拟渲染（`useState` / `useEffect`）；
- 读取 `plugin/lib/client.js`，通过 `window.__ModuleLoader__` 取组件；
- mock `fetch("http://127.0.0.1:8770/api/state")` 返回一个 session / 一个任务；
- mock `useSessions` 返回“最后一条用户消息时间”：
  - 早于任务 `startedAt` → 应显示；
  - 晚于任务 `startedAt` → 应隐藏。

## 结果（2026-11-03）

```
card: true
task: true
active rows: 2
progress: 40% / 45%
hidden after new prompt: true
```

即：

- 任务名、状态、任务级 40% 进度正确渲染；
- 两个并行进行中步骤各一行，步骤进度 45% / 30% 正确；
- 下一次提问后（`updatedAt > startedAt`）卡片返回 `null`，即隐藏。

## 限制

- 这是渲染逻辑验证，不是真实 DSH slot 环境；
- 真实 DSH 内的位置/样式/交互要等 B4 安装到 profile 后验证。
