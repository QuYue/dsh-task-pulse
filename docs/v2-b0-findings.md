# v2 B0 验证结论

目标：确认 DSH 内卡片（v2）能否在 composer 上方原生注册，以及插件怎么装。

## 1. 插槽：可以做

从 `dsh-client-ui-conversation` 的客户端 bundle 中确认：

- 原生 Todo list 注册在 **`conversation.input.dock`**：
  ```js
  ctx.slots.inject("conversation.input.dock", () => ctx.slots.register({
    name: "conversation.input.dock",
    id: "todo",
    order: 0,
    locale: "conversation"
  }, TodoDock));
  ```
- 同一位置还有 `conversation.composer.dock`（ContextMeter 等使用）；
- 插槽注册是公开 API：`ctx.slots.inject(name, () => ctx.slots.register(spec, Component))`，
  第三方 client plugin 可以注册自己的条目，用 `order` 控制与 todo 的上下顺序。

**结论**：v2 卡片可以注册到 `conversation.input.dock`，与原生 Todo 同层；
建议 `id: "live-progress-card"`, `order: 1`（todo 为 0）。

## 2. 插件形态

客户端插件包：

- `package.json` 声明 `dsh.client`（`platform: "web"`），导出 `./client`；
- client bundle 是 `window.__ModuleLoader__.load({ id, factory })` 形式，
  共享模块用 `require("react")` 等，导出 `apply(ctx)` / `inject`；
- 组件可以是普通 React 组件，slot 的 `inject` 负责传 props。

## 3. 安装路径

- `dsh plugin --profile desktop add <pkg>` 只是把参数转发给 profile 目录的 pnpm；
- 本地包可用 `file:/abs/path` 安装；
- 还需要在 `~/.dsh/profiles/desktop/cordis.patch.yml` 增加一条 Loader 条目
  （`- name: '<pkg>'`），或者把带 `dsh.bundle.patch` 的包加入 profile bundles；
- 修改 profile 需要重启 DSH Desktop 才会加载新的 Host/Client 插件；
  客户端 HMR 只在源码 `pnpm run dev:web` 时可用，打包版不行。

## 4. 数据通道

卡片需要读 board hub：

- 最简单：`fetch("http://127.0.0.1:8770/api/state")`，需要给 hub 的只读接口加 CORS；
- 备选：Host 侧插件做代理/Remote，不依赖 CORS，但多一层插件；
- 实时性：`EventSource /api/stream` 或 1–2s 轮询均可；CORS 同样适用。

## 5. 风险

- DSH client API 未承诺长期稳定，升级后需回归；
- 安装需要写 `~/.dsh`（当前 workspace-write 沙箱外），会触发一次授权；
- 修改 profile 后必须重启应用，本轮不动真实 profile，先在 repo 内做插件骨架。

## 结论

**B0 通过，可以进入 B1**：在 repo 内新增 `plugin/` 包（不依赖构建工具，
手写 `lib/client.js`），先做静态卡片；确认样式后再安装到 profile。
