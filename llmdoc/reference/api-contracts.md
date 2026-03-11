# API 契约

## 统一响应

```ts
interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: string
  meta?: {
    total?: number
    page?: number
    limit?: number
  }
}
```

## 核心接口

### 项目与实验体系
- `POST /projects`
- `GET /projects/{id}`
- `POST /projects/{id}/systems`
- `PATCH /systems/{id}`
- `GET /projects/{id}/dashboard`

### 资产
- `POST /assets/upload`
- `GET /assets/{id}`
- `GET /systems/{id}/assets`
- `POST /assets/{id}/bind`
- `GET /systems/{id}/manifest`
- `POST /systems/{id}/manifest`

### 图表与证据
- `POST /systems/{id}/figure-plans/generate`
- `PATCH /figure-plans/{id}`
- `POST /systems/{id}/evidence-matrix/generate`
- `PATCH /claims/{id}`

### 写作与审批
- `POST /systems/{id}/outline/generate`
- `GET /systems/{id}/outlines`
- `POST /outlines/{id}/confirm`
- `POST /outlines/{id}/bindings`
- `POST /systems/{id}/sections/{sectionKey}/draft`
- `GET /systems/{id}/drafts`
- `POST /drafts/{id}/review`
- `POST /drafts/{id}/approve`

### 工作流
- `POST /systems/{id}/advance`
- `GET /systems/{id}/workflow`

## 前端兼容层约束（2026-03-09）

- `GET /systems/{id}/workflow` 当前后端返回 snake_case 字段；前端 `frontend/hooks/useProjectStatus.ts` 负责把 `WorkflowSnapshot`、`WorkflowEvent`、`Blocker` 归一化为内部 camelCase 模型。
- `POST /systems/{id}/advance` 的顶层状态字段目前允许 camelCase 与 snake_case 并存；前端 `frontend/hooks/useSystemAdvance.ts` 必须兼容 `currentState/current_state`、`fromState/from_state`、`toState/to_state`。
- `POST /systems/{id}/advance` 的嵌套 `handle`、`blockers`、`snapshot` 仍以 snake_case 为主，前端必须继续按后端实际契约归一化，不得假定后端已完全切换到 camelCase。

## Claim 审批前置校验

- `PATCH /claims/{id}` 在把 claim 置为 `approved` 前，必须校验 `claim.section_ref` 是否属于当前 system 的 `SystemSection.section_key` 集合。
- 若 `section_ref` 非法，接口返回 `422 Unprocessable Entity`，并阻止该 claim 进入 approved truth layer（已批准 Evidence Matrix 真相层）。
- G4 gate 会对已批准 claims 再做一次兜底检查；G5 的 section draft 校验继续保留为最后防线。

## 异步规则

Figure Plan、Manifest、Evidence Matrix、Outline、Section Draft、Vision 校验、数据分析等动作必须立即返回任务句柄，不同步返回最终产物。

- `POST /systems/{id}/outline/generate` 返回 `202 Accepted` 与 `handle`；后台任务完成后才会写入 `Outline` 记录，并在 workflow context / task event payload 中回写 `outline_id`、`outline_version`、`outline_status`。`POST /outlines/{id}/confirm` 返回的 outline detail 现包含真实 `approvedAt`，且重复确认保持原批准时间不变。
- `POST /systems/{id}/sections/{sectionKey}/draft` 返回 `202 Accepted` 与 `handle`；后台任务完成后才会写入 `SectionDraft` 记录，并在 workflow context / task event payload 中回写 `draft_id`、`section_key`、`draft_version`、`draft_status`。后台执行会优先消费受理阶段已落入 workflow context 的标准化 `claim_ids` 快照，而不是再次从可变 outline 数据重新推导。
- 上述两个 drafts 生成端点的失败路径同样会写入 `TASK_FAILED` 事件与 `last_error`，前端应以 workflow snapshot / websocket task event 为唯一异步状态源，不要假定 202 后产物已存在；unexpected failure payload 不再包含原始异常文本。
- drafts 相关前端契约现已承接嵌套列表字段：outline list/detail 包含 `bindings`，draft list/detail 包含 `reviewComments`；其中 outline fallback 使用的 `outline_json` 同时兼容 `{ sections: [...] }` 与 list 形态。
