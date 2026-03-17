# G4 Evidence Matrix Readiness Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 让 G4 的“生成证据矩阵、确认 claims/outline、推进到 G5”形成一致的状态机、后端判定和前端交互，消除用户“明明确认完了却无法推进”的困惑。

**Architecture:** 以后端 gate review 为唯一 readiness 真相源，前端不再自行乐观推断 G4 是否完成。Evidence Matrix 重生成语义需要显式化，不能继续悄悄制造新的 latest draft claim 覆盖既有批准结果。

**Tech Stack:** FastAPI, SQLAlchemy, React, TanStack Query, Vitest, pytest

---

### Task 1: 固化现状测试，锁定当前缺陷

**Files:**
- Modify: `backend/tests/modules/gates/test_gate_review.py`
- Modify: `backend/tests/modules/evidence/test_evidence_api.py`
- Modify: `backend/tests/modules/drafts/test_drafts_api.py`
- Modify: `frontend/components/gates/EvidenceMatrixPanel.test.tsx`

**Step 1: 写失败测试，覆盖用户真实卡点**

- 后端测试一：重新生成 Evidence Matrix 后，旧 approved claim 不应被静默“最新 draft”覆盖而导致 gate 语义混乱。
- 后端测试二：confirm outline 后，系统状态不应被前端乐观视为已进入 G5。
- 前端测试一：G4 面板应显示 readiness blocker，而不是只显示计数。
- 前端测试二：未满足 per-section binding / per-section approved claim 时，G4 推进按钮不可用。

**Step 2: 运行失败测试**

Run:
```bash
pytest backend/tests/modules/gates/test_gate_review.py -q
pytest backend/tests/modules/evidence/test_evidence_api.py -q
pytest backend/tests/modules/drafts/test_drafts_api.py -q
pnpm vitest frontend/components/gates/EvidenceMatrixPanel.test.tsx
```

Expected: 至少有一部分测试失败，证明当前行为与目标不一致。

### Task 2: 统一 G4 状态机语义

**Files:**
- Modify: `backend/app/common/enums.py`
- Modify: `backend/app/modules/gates/service.py`
- Modify: `backend/app/modules/systems/service.py`
- Test: `backend/tests/modules/gates/test_gate_review.py`

**Step 1: 明确 G4/G5 边界**

- 决策并落实二选一：
- 方案 A：删除或停用“半落地”的 `Evidence_Matrix_Ready` 中间态。
- 方案 B：完整实现 `Assets_Confirmed -> Evidence_Matrix_Ready -> Outline_Ready` 两段推进。

**Step 2: 推荐采用方案 A**

- 保持 G4 内部动作多步，但 gate 通过只认一个出口：`/systems/{id}/advance`。
- `Outline_Ready` 保留为 G5 入口状态。

**Step 3: 补测试**

- 校验 gate/state 映射稳定，避免前后端再次出现“枚举有这个状态，但业务不走这里”的伪状态。

### Task 3: 显式化 Evidence Matrix 重生成语义

**Files:**
- Modify: `backend/app/modules/evidence/service.py`
- Modify: `backend/app/modules/evidence/repository.py`
- Modify: `backend/app/modules/evidence/schemas.py`
- Test: `backend/tests/modules/evidence/test_evidence_api.py`

**Step 1: 定义重生成策略**

- 推荐策略：如果系统内已存在 approved latest claims 或 confirmed outline，则重生成必须返回显式冲突信息，要求用户确认“将使现有批准结果失效”。

**Step 2: 最小实现**

- 在 `generate_evidence_matrix` 前增加冲突检测。
- 冲突时返回 409，并附带：
- `approved_latest_claim_count`
- `confirmed_outline_exists`
- `sections_affected`

**Step 3: 若允许强制重生成，再加显式参数**

- 例如 `forceRegenerate=true`。
- 强制重生成后，必须同步把相关 outline 标记 stale，并在响应里返回 invalidate summary。

**Step 4: 补测试**

- 普通重生成返回 409。
- force 重生成时，新版本 claim 创建成功，且失效信息明确。

### Task 4: 让 gate review 成为 G4 唯一 readiness 真相源

**Files:**
- Modify: `backend/app/modules/gates/service.py`
- Modify: `backend/app/common/schemas.py`
- Test: `backend/tests/modules/gates/test_gate_review.py`

**Step 1: 扩充 G4 blocker 细节**

- 为以下场景返回更细粒度 details：
- `section_missing_claims`
- `evidence_matrix_not_ready`
- `outline_not_ready`
- `section_missing_binding`
- `snapshot_stale`

**Step 2: 输出可直接渲染的 readiness summary**

- 例如：
- `sectionCount`
- `sectionsWithApprovedClaims`
- `sectionsWithBindings`
- `approvedLatestClaimCount`
- `approvedClaimsWithEvidenceCount`
- `canAdvance`

**Step 3: 补测试**

- 测试每个 blocker 的 details 完整且稳定。

### Task 5: 前端移除 G4 的乐观状态推进

**Files:**
- Modify: `frontend/hooks/useEvidence.ts`
- Modify: `frontend/hooks/useProjectStatus.ts`
- Test: `frontend/components/gates/EvidenceMatrixPanel.test.tsx`

**Step 1: 去掉 `useConfirmOutline` 的乐观 `Outline_Ready` 写入**

- 当前 confirm 成功后直接 `updateWorkflowSnapshotState(..., "Outline_Ready")`。
- 这会制造“界面像进入 G5，但 gate 其实没过”的假象。

**Step 2: 只做 query invalidation**

- 让真实 workflow snapshot 决定当前 gate/state。

**Step 3: 补测试**

- confirm outline 后，如果未调用 advance，前端仍应停留在 G4 语义。

### Task 6: 在 G4 面板内展示真实 readiness，而不是只展示统计数

**Files:**
- Modify: `frontend/components/gates/EvidenceMatrixPanel.tsx`
- Modify: `frontend/components/gates/g4/G4StatsOverview.tsx`
- Modify: `frontend/components/gates/g4/SectionOutlineList.tsx`
- Test: `frontend/components/gates/EvidenceMatrixPanel.test.tsx`

**Step 1: 新增“推进条件”区域**

- 展示：
- 每个 section 是否已有 approved latest claim
- 每个 section 是否已有 binding
- approved claims 是否都已有 evidence link
- latest outline 是否已 confirmed
- 是否存在 stale warning

**Step 2: 把 blocker 明细映射到 section**

- 不再只显示底部 blocker code。
- 在对应 section 行旁直接提示缺 claim / 缺 binding / 缺 evidence。

**Step 3: 把“生成证据矩阵”和“推进到 G5”分成不同主按钮**

- “生成证据矩阵”属于工件生成。
- “推进到 G5”属于 gate pass。

### Task 7: 给 G4 一个本地可见的推进按钮

**Files:**
- Modify: `frontend/components/gates/EvidenceMatrixPanel.tsx`
- Modify: `frontend/app/projects/[projectId]/systems/[systemId]/page.tsx`
- Modify: `frontend/hooks/useSystemAdvance.ts`
- Test: `frontend/components/gates/EvidenceMatrixPanel.test.tsx`

**Step 1: 在 G4 面板内部放置明确 CTA**

- 文案建议：`推进到 G5`
- 禁用时直接显示原因，而不是只依赖页面右上角的全局按钮。

**Step 2: CTA 仅在 readiness summary 通过时启用**

- 点击后调用 `/systems/{id}/advance`。

**Step 3: 补测试**

- blockers 存在时按钮禁用并显示原因。
- blockers 清空时按钮可点击并触发 advance。

### Task 8: 收紧前端动作约束，减少“表面完成”

**Files:**
- Modify: `frontend/components/gates/g4/ClaimRow.tsx`
- Modify: `frontend/components/gates/g4/SectionOutlineList.tsx`
- Test: `frontend/components/gates/EvidenceMatrixPanel.test.tsx`

**Step 1: 调整 claim approve 交互**

- 无 evidence link 时：
- 要么禁用“批准 Claim”
- 要么允许点击，但弹出强提示“批准后仍无法推进”

**Step 2: 调整 confirm outline 交互**

- 缺任一 section binding 时，不允许确认 outline。
- 或者允许点击，但先给出完整缺失列表，且不伪装成即将推进。

**Step 3: 补测试**

- 无 evidence link 的 claim 无法误导性批准。
- 缺 binding 时 outline confirm 不可继续。

### Task 9: 强化 EvidenceHub / GatePanel 文案

**Files:**
- Modify: `frontend/components/evidence/EvidenceHub.tsx`
- Modify: `frontend/components/gates/GatePanel.tsx`
- Test: `frontend/components/gates/EvidenceMatrixPanel.test.tsx`

**Step 1: 重写 G4/G5 文案**

- G4：强调“确认工件 != 通过 Gate”。
- G5：强调“只有在 G4 成功推进后才能生成 draft”。

**Step 2: 明确页面内路径**

- 告诉用户：
- 先生成矩阵
- 再补齐 claim evidence
- 再生成并绑定 outline
- 再确认 outline
- 最后点击推进到 G5

### Task 10: 回归测试与验收

**Files:**
- Test: `backend/tests/modules/gates/test_gate_review.py`
- Test: `backend/tests/modules/evidence/test_evidence_api.py`
- Test: `backend/tests/modules/drafts/test_drafts_api.py`
- Test: `frontend/components/gates/EvidenceMatrixPanel.test.tsx`
- Test: `frontend/components/gates/DraftPanel.test.tsx`

**Step 1: 运行后端测试**

Run:
```bash
pytest backend/tests/modules/gates/test_gate_review.py -q
pytest backend/tests/modules/evidence/test_evidence_api.py -q
pytest backend/tests/modules/drafts/test_drafts_api.py -q
```

**Step 2: 运行前端测试**

Run:
```bash
pnpm vitest frontend/components/gates/EvidenceMatrixPanel.test.tsx
pnpm vitest frontend/components/gates/DraftPanel.test.tsx
```

**Step 3: 手工验收**

- 路径一：正常流程从 G3 进入 G4，完成全部条件后可本地推进到 G5。
- 路径二：重生成矩阵时，系统明确提示会失效既有批准结果。
- 路径三：缺 claim / 缺 evidence / 缺 binding / stale 时，UI 都能明确指出卡点。
