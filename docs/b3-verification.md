# B3 交互与持久化验证

## 内容

- **折叠状态持久化**：按 session 存在 `localStorage["dsh-lp-card-open:<sessionId>"]`，
  `1` 展开 / `0` 折叠；刷新/重新挂载后恢复；
- **备注 `注`**：展开后的步骤行点 `注` 就地展开备注，不触发卡片折叠；再点收起；
- **打开 8770**：链接使用任务自己的 `urls.page`，点击在新标签打开；
- **生命周期**：B2 的“下一次提问隐藏”仍生效。

## 验证（jsdom + 轻量 hooks 模拟）

```
note button: true
note expanded: true
link: true
hidden after new prompt: true
collapsed persisted: true
```

说明：

- 初始 `localStorage` 为展开，卡片直接渲染步骤表；
- 点 `注` 后出现「备注：等待接口」；
- 看板链接为 `http://127.0.0.1:8770/r/sess-1/t1`；
- 下一提问后卡片隐藏；
- 点头部收起后 localStorage 变为 `0`。

## 限制

真实 DSH 内的 slot/样式/浏览器行为要等 B4 安装后回归。
