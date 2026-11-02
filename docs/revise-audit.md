# `revise` 计划变更能力审计

结论：**加步骤、删步骤、改步骤、改阶段都能做**，但有若干边界；本次已补上关键防护。

## 支持情况

| 场景 | 支持 | 行为 |
|---|---|---|
| 增加步骤 | ✅ | 新 id 加入计划；指定 `order` 可插到任意位置 |
| 删除步骤 | ✅ | 旧步骤标记 `superseded` 保留历史，不物理删除 |
| 修改标题/owner/阶段/size/验收/依赖 | ✅ | 按 id 匹配，事件状态保留 |
| 调整顺序 | ✅ | 改 `order`；`changes` 记录 changed |
| 删除整个阶段 | ✅ | 阶段内被删步骤会带着原阶段补回，历史不丢 |
| 已完成/失败任务追加步骤 | ✅ | 自动把任务状态改回 `running`，清空 `completedAt` |
| 重复删除同一步骤 | ✅ | 不会重复追加 superseded 记录 |
| 复用已删除步骤 id | ✅ 拒绝 | 防止旧事件污染新步骤 |
| 删除后继续 start/done 旧步骤 | ✅ 拒绝 | `_find_step` 对 superseded 报错 |
| 未知依赖 / 自依赖 / 依赖环 | ✅ 拒绝 | `_validate_plan_steps` 在 init/revise 校验 |
| 删除被依赖的步骤 | ⚠️ 允许 | 依赖指向 superseded（终态），不会永远阻塞；语义上由 Lead 判断 |
| 修改进行中步骤的 owner | ⚠️ 允许 | 不强制中断；建议先 block/revise 再换人 |
| 重命名步骤 id | ❌ | id 是事件主键；要换 id = 删除旧步骤 + 新增新步骤 |
| 展示序号 | ✅ | `view.steps[].seq` 按真实顺序生成；与内部 id 解耦 |
| 删除任务/项目 | ✅ | 走 `task rm` / `project remove`，不属于 revise |

## 本次补的防护

- `_validate_plan_steps`：重复 id、未知依赖、自依赖、依赖环；
- `_find_step`：拒绝 superseded 步骤的后续事件；
- 已 superseded 的步骤在后续 revise 中继续保留，不会因再次省略而丢失/重复；
- 已完成/失败任务加步骤自动重新打开；
- 复用的 superseded id 直接报错；
- `order` 纳入 changed 比较，重排可见。

## 仍需 Lead 注意

1. 新增步骤没写 `order` 时默认排末尾；插入已有阶段必须显式给 `order`；
2. 删步骤前看一眼谁依赖它，必要时同步改依赖；
3. 进行中步骤换 owner 先 block/resume 或 revise，避免事件归属混乱；
4. 任务已完成再追加步骤会重开任务；如果这是“新请求”，更推荐新任务。
