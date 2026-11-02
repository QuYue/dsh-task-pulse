# live-progress 排障

## 卡片不显示

按顺序检查：

1. **hub 是否在跑**

   ```bash
   B="python3 .dsh/skills/live-progress/scripts/board.py"
   $B ensure
   curl -s http://127.0.0.1:8770/api/health
   ```

   DSH 重启可能把 hub 子进程带走；`ensure` 会后台拉起。

2. **当前请求是否有任务**

   卡片只显示“最近一次用户消息之后创建的任务”。旧任务在下一次提问后隐藏是设计行为。
   当前请求需要先创建任务：

   ```bash
   $B auto --title "当前请求"
   # 或 $B init --plan-file plan.json
   ```

3. **改过 client bundle 是否重启 DSH**

   `plugin/lib/client.js` 改动后，打包版 DSH 需要重启 Desktop 才加载新 bundle；页面刷新不够。

4. **插件是否还在 profile 里**

   ```bash
   ls -l ~/.dsh/profiles/desktop/node_modules/dsh-live-progress-card
   grep -n -A 3 'dsh-live-progress-card' ~/.dsh/profiles/desktop/cordis.patch.yml
   ```

   条目必须是：

   ```yaml
   - insert:
       - id: dsh-live-progress-card
         name: "dsh-live-progress-card"
   ```

   裸 `- id: ...` 会被 profile 拒绝（`patch: entry ... not found`）。

5. **认证与端口**

   DSH Web 端口需要认证，直接用 curl 访问 `/plugins/...` 可能返回 401/404，不代表插件没加载；
   以 DSH 页面里的实际效果为准。

## 某个 session 的卡片不显示（hub 在 8771 等端口）

卡片插件会自动扫描本地 `8770–8789`，选择包含当前 session 的 hub。
如果你确认任务存在但卡片没显示，先看该 session 的 `board.py status` 输出的看板端口：

```bash
$B status | tail -2
# 看板: http://127.0.0.1:8771/r/...
```

早期插件只连 8770，而 8770 被另一个项目占用时，hub 会自动落到 8771；
新版本已支持多 hub 自动发现。仍不显示时，可以显式指定：

```js
localStorage.setItem("dsh-lp-hub", "http://127.0.0.1:8771")
```

然后刷新/重启 DSH。

## 原生 Todo 和卡片的关系

- 两者都注册在 `conversation.input.dock`：Todo 是 `order=0`，卡片是 `order=1`；
- 不改 `todos` projection，不调用 `todo_write`，互不影响；
- 原生 Todo 是客户端/会话状态，DSH 重启后通常还在；
- 卡片依赖 hub + 生命周期，所以 hub 挂了或任务早于最新提问时会消失。

## 修改卡片样式后

1. 改 `plugin/lib/client.js` 里 CSS；
2. `node --check plugin/lib/client.js`；
3. 重启 DSH Desktop；
4. 如果只是想看静态样式，可打开 `plugin/preview.html`（不加载 DSH，只做视觉预览）。

## 安装/卸载

安装：

```bash
cd plugin && ./install.sh desktop
```

卸载：

```bash
rm ~/.dsh/profiles/desktop/node_modules/dsh-live-progress-card
# 从 cordis.patch.yml 删除 dsh-live-progress-card 的 insert 条目
# 重启 DSH
```

## 看板/服务

```bash
$B ensure                 # 确保 hub
$B status                 # 当前任务
$B status --all           # 当前 session 所有任务
$B render --all           # 重建 state/BOARD
$B prune --keep 20 --dry-run
```

- hub 挂了不影响数据，重新 `ensure` 即可；
- 单任务 `BOARD.md` 始终可读；
- 端口被占时 `serve` 会自动尝试后续端口，并更新 `hub.json`。
