# TaskPulse 卡片（v3）

DSH 输入框上方的任务进度卡片，属于 `@quyue/dsh-task-pulse` 单包的一部分。

- 客户端 bundle：`lib/client.js`
- 注册 slot：`conversation.input.dock`，`id: task-pulse-card`，`order: 1`
- 数据：hub 8770（优先，兜底扫描 8770–8789）
- 生命周期（v2）：当前 session 最新任务创建后显示；完成后保留；下一次提问隐藏；
  不按 current project 过滤

开发检查：

```bash
node --check lib/client.js
node tests/smoke-test.cjs
```

安装/重启见根目录 `install.sh` 与 `README.md`。
