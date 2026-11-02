# live-progress demo

两个同时进行的项目，用来展示看板的全部能力：

| 项目 | 类型 | 演示内容 |
|---|---|---|
| `demo-wordcount` | 本地 | 主 agent + coder + reviewer + 后台 job；**并行**步骤；运行中途**计划升版**（新增 CSV 步骤，旧步骤不删）；步骤证据；完成后关闭 |
| `demo-remote` | ingest（远程推送） | 服务器侧用 token 把 plan/events **POST 到本地 hub**，本地总览同时出现两个项目 |

## 运行

```bash
# 仓库根目录下
python3 demo/run_demo.py --open        # 正常速度约 45 秒
python3 demo/run_demo.py --fast        # 约 15 秒，适合冒烟
python3 demo/run_demo.py --fresh       # 先清掉上次 demo 数据
```

脚本默认会在 `127.0.0.1:8770` 启动 hub，并在演示结束后保持运行，方便你刷新页面回看；
`Ctrl+C` 退出。若 8770 已有看板服务，会直接复用。

## 你会看到

1. 总览页两张项目卡同时更新；
2. 进入本地项目：coder 与 reviewer 两条泳道同时走，后台 job 单独一行；
3. 运行中计划从 v1 升到 v2，新增 `s6`，变更记录出现在看板；
4. 完成/失败/阻塞/升版会触发通知（页面打开时用浏览器通知，页面关闭时用系统通知）；
5. 完成后 `BOARD.md` 与 `state.json` 留在各自 run 目录，可离线回看。

## 数据位置

- 本地项目：`demo/demo_a/.dsh/progress/`
- hub 与远程镜像：`demo/.hub/`
- 两者都在 `.gitignore` 中，不会进入 git。

## 说明

演示里的“写代码/审查/测试”是脚本模拟的步骤，不会真的改动 `demo_a/task/` 里的示例项目；
产物写在 `demo/demo_a/artifacts/`，用于给步骤提供证据路径。
