# G4 错误详情面板设计

**日期**: 2026-03-18

**背景**

当前 G4 中的 `Evidence Matrix 生成失败` 只有一行字符串提示，用户看不到后端已返回的冲突明细，也无法直接跳到可修复的位置。更糟的是，用户容易把“资产已确认”误解成“允许重建 Evidence Matrix”，但后端实际判定的是后续产物是否已存在。

本次设计目标是把 G4 的错误从“提示文案”升级成“可解释、可定位、可执行”的错误处理流。

---

## 1. 问题定义

### 1.1 当前真实规则

G4 的 Evidence Matrix 普通重建请求在以下任一条件成立时会被后端拒绝：

- 存在最新版本且状态为 `approved` 的 claims
- 存在状态为 `confirmed` 或 `approved` 的 outline

这与“资产是否已确认”无关。资产确认只是 G3/G4 的输入条件，不代表允许覆盖后续人工确认过的产物。

### 1.2 当前体验缺陷

- 前端 `ApiError` 只保留 `status` 和 `error` 文案，丢失了后端 `data.code` 与 `data.details`
- G4 面板只能展示一行错误字符串，无法解释冲突原因
- 用户看不到受影响章节，也没有“去 Claims / 去 Outline / 去推进条件”的定位入口
- 当前只有“继续重建”确认框，没有二级详情层，无法承载后续更多错误类型

---

## 2. 设计目标

- 让用户在 G4 中一眼看懂“为什么失败”
- 提供可执行的修复动作，而不是只给报错
- 保留“强制重建”作为显式破坏性操作
- 为后续 `outline_not_ready`、`snapshot_stale`、`gate_blocked` 等错误复用同一套二级详情机制

## 3. 非目标

- 本轮不做跨页面的全局错误中心
- 本轮不重构所有模块的错误 UI，只先覆盖 G4
- 本轮不改变 G4 的业务规则，只改变错误表达和可操作性

---

## 4. 选型结论

采用 **G4 内二级错误详情面板**，而不是单纯升级错误卡片，也不是新开独立路由页。

### 原因

- 不打断用户当前上下文，仍停留在 G4
- 信息容量足够，能承载原因、风险和操作建议
- 后续同类错误可复用，不会把主面板挤成错误文案堆

---

## 5. 方案概览

```text
一级：G4 主面板显示简短错误摘要
  ↓
二级：打开右侧错误详情面板
  ↓
动作：定位到对应模块 / 强制重建 / 刷新快照
```

### 一级错误摘要

继续保留在 G4 主面板中的短提示，示例：

```text
Evidence Matrix 生成失败：当前已有已批准 Claims 或已确认 Outline，不能直接重建。
```

并新增按钮：

- `查看详情`
- `继续重建`（仅冲突类错误显示）

### 二级错误详情面板

面板展示以下内容：

- 错误标题
- 错误码
- 简洁解释
- 影响范围
- 解决建议
- 快捷动作

---

## 6. 数据契约

### 6.1 前端 API 错误模型升级

当前 `frontend/lib/api.ts` 中的 `ApiError` 需要保留以下字段：

- `status`
- `message`
- `code`
- `details`

建议新增统一类型：

```ts
type ApiErrorPayload = {
  code?: string
  details?: Record<string, unknown>
}
```

`apiRequest()` 在非 2xx 时解析：

- `error` -> 作为 message
- `data.code` -> 作为结构化错误码
- `data.details` -> 作为结构化详情

### 6.2 后端错误码细化

当前 Evidence Matrix 重建冲突返回的 `code` 只是通用 `conflict`，对前端做动作映射不够稳定。

建议将这类错误细化为：

- `evidence_matrix_regeneration_conflict`

并保留现有 `details`：

- `approved_latest_claim_count`
- `confirmed_outline_count`
- `sections_affected`
- `force_regenerate`

如需增强可读性，可补充：

- `resolution_targets`: `["claims", "outline", "readiness"]`

---

## 7. 错误详情面板内容模型

前端新增统一的 G4 错误解析层，将 `ApiError` 映射为可渲染的详情对象。

建议模型：

```ts
type G4IssueDetail = {
  title: string
  summary: string
  code: string
  severity: "warning" | "error"
  impactItems: string[]
  recommendedActions: G4IssueAction[]
  allowForceRegenerate: boolean
}
```

动作模型：

```ts
type G4IssueAction =
  | { kind: "scroll"; target: "claims" | "outline" | "readiness" | "section"; label: string; sectionKey?: string }
  | { kind: "mutation"; target: "force-regenerate"; label: string; confirm: boolean }
```

---

## 8. 交互设计

### 8.1 面板入口

当 `generateEvidenceMatrix` 返回错误时：

- 主面板显示错误摘要
- `查看详情` 打开右侧二级面板
- 若为可强制继续的冲突，则同时显示 `继续重建`

### 8.2 面板动作

对于 `evidence_matrix_regeneration_conflict`：

- `去 Claims`：滚动并聚焦到 Claim 列表区域
- `去 Outline`：滚动并聚焦到提纲区域
- `去推进条件`：滚动到 readiness 区块
- `查看受影响章节`：高亮 `sections_affected` 对应 section
- `确认后强制重建`：再次弹确认框，执行 `forceRegenerate`

### 8.3 跳转语义

首版“跳转”定义为 **G4 页面内模块定位**，不新增路由跳转。

实现手段：

- 为 `Claims`、`Outline`、`推进条件`、`Section Outline List` 增加 DOM 锚点或 ref
- 点击动作后 `scrollIntoView`
- 被定位的模块短暂高亮，帮助用户确认已跳到正确位置

这是最低成本且最符合当前页面结构的实现；后续若出现跨页面修复场景，再扩展成路由跳转。

---

## 9. 与现有 G4 的耦合点

### 9.1 前端

受影响文件预计包括：

- `frontend/lib/api.ts`
- `frontend/hooks/useEvidence.ts`
- `frontend/components/gates/EvidenceMatrixPanel.tsx`
- 新增 `frontend/components/gates/g4/G4IssueDetailPanel.tsx`
- 新增或扩展 `frontend/components/gates/g4` 下的锚点与高亮逻辑

### 9.2 后端

受影响文件预计包括：

- `backend/app/modules/evidence/service.py`
- `backend/tests/modules/evidence/test_evidence_api.py`

后端改动应保持现有 409 语义不变，只提升错误码可识别性与详情稳定性。

---

## 10. 测试策略

### 10.1 后端

- 普通重建在存在 approved latest claims / confirmed outline 时仍返回 409
- 错误码变为 `evidence_matrix_regeneration_conflict`
- `details` 中的计数和 `sections_affected` 保持稳定

### 10.2 前端

- `ApiError` 能解析 `code/details`
- G4 冲突错误出现后，主面板显示 `查看详情`
- 打开详情面板后，展示冲突原因、计数与受影响章节
- 点击 `去 Claims / 去 Outline / 去推进条件` 会调用定位逻辑
- 点击 `确认后强制重建` 会带 `forceRegenerate: true`

---

## 11. 后续扩展点

当前结构应预留给以下错误复用：

- `outline_not_ready`
- `snapshot_stale`
- `gate_blocked`
- `section_missing_binding`
- `evidence_matrix_not_ready`

扩展规则：

- 一级仍用简短摘要
- 二级统一走 `Issue Detail Panel`
- 每个错误码拥有自己的动作映射

---

## 12. 最终决策

本次实现采用以下边界：

- 在 G4 内新增统一的二级错误详情面板
- 前端不再丢弃后端错误 `code/details`
- Evidence Matrix 冲突错误升级为结构化可操作错误
- 首版跳转为 G4 页面内模块定位，不新开路由
- 保留“强制重建”作为显式确认后的危险操作

这能在不改变业务规则的前提下，把“为什么失败”和“去哪里修”两件事都交代清楚。
