# Workflow 与 Gates

## 固定门禁映射

- G0 → `System_Defined`
- G1 → `Figure_Plan_Ready`
- G2 → `Data_Uploaded + Analysis_Ready`
- G3 → `Assets_Confirmed`
- G4 → `Evidence_Matrix_Ready + Outline_Ready`
- G5 → `Chapter_Approved`

## 状态推进原则

- `POST /systems/{id}/advance` 只表达用户推进请求。
- 前端 `useSystemAdvance` 必须把响应归一化后再进入 UI：顶层状态字段兼容 camelCase 与 snake_case，嵌套 `handle` / `blockers` / `snapshot` 继续按后端 snake_case 契约读取并转换。
- 真正推进由 gates 校验 + workflow 决策完成。
- 所有阻塞必须可结构化解释（Blocker: code + message + gate + requiredChecks）。

## 前端 Gate 状态派生

前端通过 `useProjectStatus` hook 获取 workflow snapshot。`/systems/{id}/workflow` 当前以 snake_case 返回 `WorkflowSnapshot` / `WorkflowEvent` / `Blocker`，前端先做归一化，再调用 `deriveGateItems` 派生每个 gate 的视觉状态。

`normalizeWorkflowSnapshot` 在计算 `currentGate` 时优先根据 `current_state` 推导，仅在状态无法映射 gate 时才回退到后端 `current_gate`。这样可以规避 gate 刚通过时后端 `current_gate` 暂未更新、但 `current_state` 已前进所造成的 GateNav / Workbench 错位。

| 条件 | 视觉状态 |
|------|----------|
| 无 snapshot | `neutral`（全部 gate） |
| gate index < active gate index | `passed` |
| gate index == active gate index | `active` |
| gate index > active gate index | `locked` |

GateNav 渲染真实 gateItems，不再依赖默认 placeholder。

## G2 子状态（前端映射）

G2 阶段在前端进一步细分为三个子状态，用于 EvidenceHub 和 GatePanel 的内容映射：
- `Data_Pending` — 等待上传
- `Data_Uploaded` — 等待分析
- `Analysis_Ready` — 可推进至 G3

## Temporal 负责

当前仓库中的 `system_workflow.py` 仍是薄适配层。Phase 2 继续采用 thin workflow / task event 模式承接生成动作与状态回写，不扩 Temporal 长流程。

G0-G5 全链闭环完成后，再评估是否扩展以下职责：

- 长流程编排
- 等待用户
- 退回修改
- 失败重试
- 恢复执行
- query / signal

## G4/G5 与 approved truth layer 约束

- 已批准 claims 是 Evidence Matrix approved truth layer（已批准真相层）的输入集合。
- `PATCH /claims/{id}` 在把 claim 置为 approved 前，必须校验 `claim.section_ref` 是否属于该 system 的 `SystemSection.section_key` 集合；非法时返回 `422`，阻止 claim 进入 approved。
- G4 gate 在审查 `Evidence_Matrix_Ready` 时，会对所有已批准 claims 的 `section_ref` 做兜底检查；若存在非法值，则返回 blocker：`code=approved_claim_sections_invalid`、`message=Approved claims reference undefined sections.`、`required_checks=[Evidence_Matrix_Ready]`。
- G5 生成 section draft 的既有 section 校验继续保留，作为最后防线，而不是首道防线。
- 当前 drafts 收口事实：outline confirm 会写入并保留 `approved_at` / `approvedAt`；section draft 后台执行优先消费受理阶段已写入 workflow context 的标准化 `claim_ids` 快照，避免 `202 Accepted` 之后 outline/claim 变化导致执行输入漂移；unexpected failure payload 不再暴露原始内部异常文本；用于 fallback 的 `outline_json` 同时兼容 `{ sections: [...] }` 与 list 形态。
- 前端系统页现在除 `workflow.state_changed` / `gate.passed` / `gate.blocked` 外，也会在 `task.succeeded` / `task.failed` 时刷新 workflow，从而让 G4/G5 异步生成完成后的工作台状态及时回到后端真相。
- 因此，非法 `section_ref` 不应在 G4/G5 之前进入 approved truth layer。

## 非法行为

- 前端直接决定可推进状态
- executor 直接写业务真相
- 未过 G4/G5 就生成结论性正文
- 允许非法 `section_ref` 的 claim 进入 approved truth layer
