# TaskPulse 排障

## 先确认 hub

```bash
B="python3 assets/task-pulse/scripts/board.py"
$B ensure
curl -s http://127.0.0.1:8770/api/health
```

所有项目共用 **8770** 一个 hub；`ensure` 已运行则直接复用，不新起服务。

## 卡片不显示

1. hub 是否在跑（上面）；
2. 当前请求之后是否创建了任务：旧任务在下一次提问后隐藏是设计行为；
3. 改过 `lib/client.js` 是否重启 DSH Desktop；
4. profile 中是否有 `@quyue/dsh-task-pulse`：
   ```bash
   ls -l ~/.dsh/profiles/desktop/node_modules/@quyue/dsh-task-pulse
   grep -n -A 3 'task-pulse' ~/.dsh/profiles/desktop/cordis.patch.yml
   ```
5. DSH 页面需要认证，curl `/plugins/...` 401/404 不代表插件没加载。

## 原生命令 `/tp` 不可用

- 确认插件已加载并重启；
- 查看 DSH 命令列表（输入 `/`）；
- `/tp server status` 应返回 hub 与当前任务。

## 修改卡片

```bash
node --check lib/client.js
node tests/smoke-test.cjs
```

静态预览：`dev/preview.html`；改完 client bundle 需重启 DSH。

## 看板/数据

```bash
$B status
$B status --all
$B render --all
$B prune --keep 20 --dry-run
```

## 安装/卸载

见 [b4-install.md](b4-install.md)。
