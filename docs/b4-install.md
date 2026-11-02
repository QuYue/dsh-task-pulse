# v2 卡片安装（B4）

## 目标环境

- DSH **0.2.1-rc.5**（Desktop）
- Desktop profile：`~/.dsh/profiles/desktop`
- 客户端 API 未承诺长期稳定，升级 DSH 后需要回归

## 安装

```bash
cd live-progress/plugin
./install.sh            # 默认 desktop
# 或
./install.sh desktop
```

脚本做两件事：

1. `dsh plugin --profile desktop add file:<plugin>`（pnpm 装进 profile）；
2. 在 `~/.dsh/profiles/desktop/cordis.patch.yml` 追加：

```yaml
- id: dsh-live-progress-card
  name: "dsh-live-progress-card"
```

然后**重启 DSH Desktop**。

## 验证

1. 打开一个会话，发起一次请求并 `init` 一个 live-progress 任务；
2. 输入框上方应出现卡片，默认折叠；
3. 展开后应看到步骤表、`注`、看板链接；
4. 下一次提问后卡片消失，直到新任务创建。

## 卸载

```bash
dsh plugin --profile desktop remove dsh-live-progress-card
# 并从 cordis.patch.yml 删除 - id: dsh-live-progress-card 两行
```

## 风险

- 卡片是 profile 插件，不是 DSH 本体；DSH 升级可能改变 slot/client API；
- 若 client bundle 加载失败，先移除 patch 条目/卸载再重启。
