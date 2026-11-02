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

## v2.0.0 — in progress

DSH 内 composer dock 卡片视图，与网页版并存。规格见
[docs/v2-card-spec.md](docs/v2-card-spec.md)。
