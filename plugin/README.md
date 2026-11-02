# dsh-live-progress-card (v2 B1)

DSH 输入框上方的 live-progress 卡片（静态骨架阶段）。

- 位置：`conversation.input.dock`（与原生 Todo 同层，`order: 1`）
- 范围：当前 session 最近一次提问的任务（B2 接入）
- 内容：任务进度表；折叠/展开；备注 `注`；打开 8770

## 当前状态（B1）

- `lib/client.js`：客户端 bundle（`window.__ModuleLoader__.load`），注册 dock 卡片；
  目前使用 **静态示例数据**；
- `lib/index.js`：Host 侧空实现（无行为）；
- `preview.html`：不安装 DSH 就能看的静态样式（浏览器直接打开）。

## B1 验收

1. `node --check plugin/lib/client.js` 通过；
2. 打开 `plugin/preview.html` 能看到折叠卡片，点击头部展开步骤表，点 `注` 展开备注；
3. `node plugin/smoke-test.cjs` 验证 bundle 注册到 `conversation.input.dock`；
4. 尚未安装到 DSH（安装属于 B4）。

## 安装（B4 再做，先记录）

```bash
# 1) 装进 Desktop profile（本地包）
dsh plugin --profile desktop add file:/Users/quyue/My_Data/My_Projects/DeepSeek_Harness/live-progress/plugin

# 2) 在 ~/.dsh/profiles/desktop/cordis.patch.yml 增加 Loader 条目
- name: 'dsh-live-progress-card'

# 3) 重启 DSH Desktop
```

数据通道需要给 hub 加只读 CORS（B2）。
