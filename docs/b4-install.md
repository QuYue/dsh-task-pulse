# TaskPulse 安装

## 单包安装

```bash
cd dsh-task-pulse
./install.sh desktop
```

脚本在 Desktop profile 中：

1. 建 symlink：`node_modules/@quyue/dsh-task-pulse` → 本仓库；
2. 在 `cordis.patch.yml` 追加：

```yaml
- insert:
    - id: task-pulse
      name: "@quyue/dsh-task-pulse"
```

3. 重启 DSH Desktop。

## 验证

- 输入 `/task-pulse`：skill 可用；
- 输入 `/tp server status`：原生命令可用；
- 页面卡片与 8770 看板显示当前任务。

## 卸载

```bash
rm ~/.dsh/profiles/desktop/node_modules/@quyue/dsh-task-pulse
# 从 cordis.patch.yml 删除 task-pulse 的 insert 条目
```
