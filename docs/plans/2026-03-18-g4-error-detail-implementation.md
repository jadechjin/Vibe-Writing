# G4 Error Detail Panel Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为 G4 的 Evidence Matrix 冲突与后续门禁错误提供统一的二级错误详情面板，展示结构化原因、影响范围和可跳转修复动作。

**Architecture:** 保持后端 409 语义不变，但把冲突错误细化成稳定错误码，并确保前端完整解析 `message/code/details`。G4 主面板继续显示一级摘要，二级详情由独立的 `Issue Detail Panel` 承载，动作通过页内锚点定位到 Claims、Outline、推进条件等模块。

**Tech Stack:** FastAPI, SQLAlchemy, React, TypeScript, TanStack Query, pytest, Vitest

---

### Task 1: 固化后端错误契约

**Files:**
- Modify: `backend/app/modules/evidence/service.py`
- Modify: `backend/tests/modules/evidence/test_evidence_api.py`

**Step 1: 写失败测试**

在 `backend/tests/modules/evidence/test_evidence_api.py` 中新增或调整断言：

- 普通生成冲突时状态码仍为 `409`
- 返回 `data.code == "evidence_matrix_regeneration_conflict"`
- 返回 `data.details.approved_latest_claim_count`
- 返回 `data.details.confirmed_outline_count`
- 返回 `data.details.sections_affected`

**Step 2: 运行失败测试**

Run:
```bash
pytest backend/tests/modules/evidence/test_evidence_api.py -q
```

Expected: 现有断言会因错误码仍是 `conflict` 而失败。

**Step 3: 最小实现**

修改 `backend/app/modules/evidence/service.py` 中冲突分支：

- 将 `code=ErrorCode.CONFLICT.value` 改为专用错误码 `evidence_matrix_regeneration_conflict`
- 保持 `status_code=409`
- 保持现有 `details`

**Step 4: 运行测试确认通过**

Run:
```bash
pytest backend/tests/modules/evidence/test_evidence_api.py -q
```

Expected: 相关测试通过，其他现有用例不回归。

### Task 2: 让前端保留结构化错误信息

**Files:**
- Modify: `frontend/lib/api.ts`
- Test: `frontend/hooks/useEvidence.test.tsx`

**Step 1: 写失败测试**

在 `frontend/hooks/useEvidence.test.tsx` 或新增 API 客户端测试中覆盖：

- 服务端返回 `{ success: false, error, data: { code, details } }`
- `ApiError` 实例应持有 `status`
- `ApiError` 实例应持有 `code`
- `ApiError` 实例应持有 `details`

**Step 2: 运行失败测试**

Run:
```bash
npx vitest run hooks/useEvidence.test.tsx --config vitest.config.ts
```

Expected: 测试因 `ApiError` 尚未暴露 `code/details` 而失败。

**Step 3: 最小实现**

修改 `frontend/lib/api.ts`：

- 新增 `ApiErrorPayload` 类型
- 扩展 `ApiError` 构造函数，支持 `code/details`
- `apiRequest()` 在非 2xx 时解析 `body.data.code` 与 `body.data.details`

**Step 4: 运行测试确认通过**

Run:
```bash
npx vitest run hooks/useEvidence.test.tsx --config vitest.config.ts
```

Expected: 新增测试通过，已有 `forceRegenerate` 用例保持通过。

### Task 3: 提取 G4 错误解析器

**Files:**
- Create: `frontend/components/gates/g4/issueDetails.ts`
- Modify: `frontend/components/gates/EvidenceMatrixPanel.tsx`
- Test: `frontend/components/gates/EvidenceMatrixPanel.test.tsx`

**Step 1: 写失败测试**

在 `frontend/components/gates/EvidenceMatrixPanel.test.tsx` 中新增断言：

- 冲突错误出现时显示 `查看详情`
- 点击后出现错误详情标题
- 面板中显示 approved claims 数量、confirmed outline 数量、受影响章节

**Step 2: 运行失败测试**

Run:
```bash
npx vitest run components/gates/EvidenceMatrixPanel.test.tsx --config vitest.config.ts
```

Expected: 当前实现没有详情面板，测试失败。

**Step 3: 写最小解析器**

在 `frontend/components/gates/g4/issueDetails.ts` 中实现：

- `resolveG4IssueDetail(error, blockers)` 或同等函数
- 将 `evidence_matrix_regeneration_conflict` 映射为：
  - 标题
  - 摘要
  - impactItems
  - recommendedActions
  - `allowForceRegenerate: true`

**Step 4: 运行测试确认解析生效**

Run:
```bash
npx vitest run components/gates/EvidenceMatrixPanel.test.tsx --config vitest.config.ts
```

Expected: 新增详情数据至少能被渲染。

### Task 4: 新增 G4 二级错误详情面板

**Files:**
- Create: `frontend/components/gates/g4/G4IssueDetailPanel.tsx`
- Modify: `frontend/components/gates/EvidenceMatrixPanel.tsx`
- Test: `frontend/components/gates/EvidenceMatrixPanel.test.tsx`

**Step 1: 写失败测试**

补充测试覆盖：

- 详情面板默认关闭
- 点击 `查看详情` 后打开
- 面板中展示：
  - 错误标题
  - 错误码
  - 影响项列表
  - 动作按钮

**Step 2: 运行失败测试**

Run:
```bash
npx vitest run components/gates/EvidenceMatrixPanel.test.tsx --config vitest.config.ts
```

Expected: 详情面板相关断言失败。

**Step 3: 写最小实现**

新增 `G4IssueDetailPanel.tsx`：

- 接收 `issue`, `isOpen`, `onClose`, `onAction`
- 使用现有样式体系实现右侧详情面板
- 不引入新的全局依赖

在 `EvidenceMatrixPanel.tsx` 中：

- 保存 `selectedIssue` / `isIssuePanelOpen`
- 保留一级错误摘要
- 新增 `查看详情` 按钮
- 渲染详情面板

**Step 4: 运行测试确认通过**

Run:
```bash
npx vitest run components/gates/EvidenceMatrixPanel.test.tsx --config vitest.config.ts
```

Expected: 面板开合与详情展示通过。

### Task 5: 接通页内定位动作

**Files:**
- Modify: `frontend/components/gates/EvidenceMatrixPanel.tsx`
- Modify: `frontend/components/gates/g4/ClaimList.tsx`
- Modify: `frontend/components/gates/g4/SectionOutlineList.tsx`
- Test: `frontend/components/gates/EvidenceMatrixPanel.test.tsx`

**Step 1: 写失败测试**

新增测试覆盖：

- 点击 `去 Claims` 时触发 claims 区域定位
- 点击 `去 Outline` 时触发 outline 区域定位
- 点击 `去推进条件` 时触发 readiness 区域定位

如果 DOM `scrollIntoView` 不便直接断言，可改为断言：

- 对应区域获得 `data-highlighted="true"`
- 或回调函数被触发

**Step 2: 运行失败测试**

Run:
```bash
npx vitest run components/gates/EvidenceMatrixPanel.test.tsx --config vitest.config.ts
```

Expected: 当前没有定位逻辑，测试失败。

**Step 3: 写最小实现**

在 `EvidenceMatrixPanel.tsx` 中：

- 为 Claims、Outline、推进条件容器挂 ref
- 封装 `focusModule(target)`：
  - `scrollIntoView({ behavior: "smooth", block: "center" })`
  - 设置短暂高亮状态

必要时给 `ClaimList` / `SectionOutlineList` 补透传容器属性。

**Step 4: 运行测试确认通过**

Run:
```bash
npx vitest run components/gates/EvidenceMatrixPanel.test.tsx --config vitest.config.ts
```

Expected: 定位行为可观测，测试通过。

### Task 6: 保留强制重建并接入详情面板动作

**Files:**
- Modify: `frontend/components/gates/EvidenceMatrixPanel.tsx`
- Modify: `frontend/components/gates/EvidenceMatrixPanel.test.tsx`

**Step 1: 写失败测试**

补充断言：

- 详情面板中的 `确认后强制重建` 会先打开确认框
- 最终调用 `mutate({ forceRegenerate: true })`

**Step 2: 运行失败测试**

Run:
```bash
npx vitest run components/gates/EvidenceMatrixPanel.test.tsx --config vitest.config.ts
```

Expected: 当前只有主卡片入口，详情面板内动作尚不存在。

**Step 3: 写最小实现**

在 `EvidenceMatrixPanel.tsx` 中：

- 让详情面板动作复用现有 `ConfirmDialog`
- 统一走现有 `generateEvidenceMatrix.mutate({ forceRegenerate: true })`
- 保留主卡片中的 `继续重建`，避免回归

**Step 4: 运行测试确认通过**

Run:
```bash
npx vitest run components/gates/EvidenceMatrixPanel.test.tsx --config vitest.config.ts
```

Expected: 主入口和详情入口都可触发强制重建。

### Task 7: 补充端到端回归验证

**Files:**
- Modify: `backend/tests/modules/evidence/test_evidence_api.py`
- Modify: `frontend/hooks/useEvidence.test.tsx`
- Modify: `frontend/components/gates/EvidenceMatrixPanel.test.tsx`

**Step 1: 运行后端测试**

Run:
```bash
pytest backend/tests/modules/evidence/test_evidence_api.py -q
```

Expected: 所有 Evidence Matrix 相关后端测试通过。

**Step 2: 运行前端测试**

Run:
```bash
npx vitest run hooks/useEvidence.test.tsx components/gates/EvidenceMatrixPanel.test.tsx --config vitest.config.ts
```

Expected: 详情面板、错误解析、强制重建相关测试全部通过。

**Step 3: 运行类型检查**

Run:
```bash
npm --prefix frontend run typecheck
```

Expected: TypeScript 无新增错误。

**Step 4: 提交前人工检查**

- 验证 G4 中冲突错误的摘要文案是否简洁
- 验证详情面板是否能看清原因与后续动作
- 验证页内定位不会把用户滚到错误位置

**Step 5: Commit**

```bash
git add backend/app/modules/evidence/service.py backend/tests/modules/evidence/test_evidence_api.py frontend/lib/api.ts frontend/components/gates/EvidenceMatrixPanel.tsx frontend/components/gates/g4/G4IssueDetailPanel.tsx frontend/components/gates/g4/issueDetails.ts frontend/hooks/useEvidence.test.tsx frontend/components/gates/EvidenceMatrixPanel.test.tsx docs/plans/2026-03-18-g4-error-detail-design.md docs/plans/2026-03-18-g4-error-detail-implementation.md
git commit -m "feat(g4): add actionable error detail panel"
```
