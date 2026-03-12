# 前端工作台结构

**最后更新：** 2026-03-09

## 页面层次与路由

前端采用 Next.js App Router，页面分为三个层级，**只有系统工作台页使用 MainShell 壳层**：

| 路由 | 页面 | 壳层 | 说明 |
|------|------|------|------|
| `/` | 根页面 | — | Server Component，`redirect("/projects")` |
| `/projects` | 项目列表 | 独立页（无 MainShell） | 自带背景与容器样式 |
| `/projects/[projectId]` | 项目详情 | 独立页（无 MainShell） | 展示体系列表、创建体系 |
| `/projects/[projectId]/systems/[systemId]` | 系统工作台 | MainShell 包裹 | 门禁导航 + 双栏工作区 + 状态托盘 |

### 根 layout 职责

`frontend/app/layout.tsx` 只负责 `<html>` / `<body>` / `<Providers>` 包裹，不包含 MainShell 或 GateNav。这样项目列表页和项目详情页不会被错误套入工作台壳层。

## 系统工作台装配（核心）

系统页 (`frontend/app/projects/[projectId]/systems/[systemId]/page.tsx`) 是唯一使用 MainShell 的页面。装配流程：

```text
SystemPage
  ├── useProjectStatus(systemId) → snapshot + gateItems
  ├── useSystemAdvance(systemId) → advance mutation
  ├── useWorkflowInvalidation(systemId) → invalidation callback
  │
  ├── 组装 evidencePanel = <EvidenceHub snapshot gateKey latestBlockers />
  ├── 组装 workbenchPanel = <GatePanel snapshot gateKey gateVisualState latestBlockers latestEvent />
  ├── 组装 statusTray = <StatusTray projectId systemId onInvalidate />
  │
  └── <MainShell gates={gateItems} evidencePanel workbenchPanel statusTray>
        ├── Back to Project 链接
        ├── System header + Advance Gate 按钮
        └── AdvanceOutcome 结果展示
      </MainShell>
```

## 关键布局组件

### MainShell (`frontend/components/layout/MainShell.tsx`)
- 接收 `gates`, `evidencePanel`, `workbenchPanel`, `statusTray` 作为 props
- 渲染 GateNav（顶部门禁导航）
- 渲染 ProjectWorkspace（双栏工作区 + 状态托盘）
- `gates` 默认为 `DEFAULT_GATE_PLACEHOLDERS`（neutral 状态），系统页传入真实 gateItems

### GateNav (`frontend/components/layout/GateNav.tsx`)
- 顶部固定（sticky），6 列 grid 展示 G0-G5
- 支持 5 种视觉状态：`neutral | locked | active | passed | pending`
- 每个 gate 卡片包含 key badge、状态标签、标题、摘要

### ProjectWorkspace (`frontend/components/layout/ProjectWorkspace.tsx`)
- 双栏布局：左栏 Evidence Hub（0.95fr），右栏 Workbench（1.45fr）
- 底部 StatusTray 条件渲染
- 每栏有 WorkspacePanel 包裹（eyebrow + title + subtitle + body）
- 未传入面板时使用默认占位 slot

## 工作区面板

### EvidenceHub (`frontend/components/evidence/EvidenceHub.tsx`)
- 左栏面板，根据当前 gateKey 和 currentState 映射内容
- G0-G5 每个阶段有对应的标题、描述、下一步动作、提示
- G2 阶段根据子状态（Data_Pending / Data_Uploaded / Analysis_Ready）细分
- 展示当前 blockers 列表

### GatePanel (`frontend/components/gates/GatePanel.tsx`)
- 右栏面板，根据 gateKey + gateVisualState + currentState 映射工作区内容
- G2/G4/G5 阶段有子状态细分
- 包含 context bar（项目名/系统名/gate 信息）
- 内嵌 WorkflowPanel 展示工作流快照

### WorkflowPanel (`frontend/components/drafting/WorkflowPanel.tsx`)
- 展示 workflow snapshot 摘要（state / gate / status / version）
- 展示最新事件（event type + message + time）
- 展示当前 blockers 列表
- 展示 last error（如有）

## 关键 hooks

| Hook | 文件 | 用途 |
|------|------|------|
| `useProjectStatus` | `hooks/useProjectStatus.ts` | 查询 workflow snapshot，派生 gateItems |
| `useWorkflowInvalidation` | `hooks/useProjectStatus.ts` | 手动触发 workflow query 刷新 |
| `useSystemAdvance` | `hooks/useSystemAdvance.ts` | 发起 advance mutation |
| `useProjectList` | `hooks/useProjects.ts` | 项目列表查询 |
| `useProjectDetail` | `hooks/useProjects.ts` | 项目详情查询 |
| `useCreateProject` | `hooks/useProjects.ts` | 创建项目 mutation |
| `useCreateSystem` | `hooks/useProjects.ts` | 创建体系 mutation |
| `useWebSocket` | `hooks/useWebSocket.ts` | WebSocket 事件订阅 |

## 数据流

```text
SystemPage
  │
  ├── useProjectStatus → GET /systems/{id}/workflow
  │     ├── 接收 snake_case WorkflowSnapshot / WorkflowEvent / Blocker
  │     ├── normalizeWorkflowSnapshot(...) → WorkflowSnapshot
  │     └── deriveGateItems(snapshot) → GateStatusItem[] → GateNav
  │
  ├── useSystemAdvance → POST /systems/{id}/advance
  │     ├── 兼容顶层 camelCase 与 snake_case 状态字段
  │     ├── 归一化嵌套 snake_case handle / blockers / snapshot
  │     └── AdvanceOutcome 组件渲染结果
  │
  └── StatusTray → useWebSocket → /ws/tasks
        └── onInvalidate → queryClient.invalidateQueries → 刷新 snapshot
```

## G1/G2/G3 前端接入恢复事实（2026-03-09）

- `frontend/hooks/useProjectStatus.ts` 现在负责把 `/systems/{id}/workflow` 返回的 snake_case `WorkflowSnapshot`、`WorkflowEvent`、`Blocker` 统一归一化为前端内部使用的 camelCase 模型，再驱动 GateNav / EvidenceHub / GatePanel / WorkflowPanel。
- `frontend/hooks/useSystemAdvance.ts` 现在负责把 `/systems/{id}/advance` 响应归一化为稳定的 `AdvanceResponse`：顶层 `currentState` / `fromState` / `toState` 同时兼容 camelCase 与 snake_case，嵌套 `handle`、`blockers`、`snapshot` 继续按 snake_case 读取后统一转换。
- `normalizeWorkflowSnapshot` 在派生 `currentGate` 时优先信任 `current_state`，仅在无法映射 gate 时才回退到后端 `current_gate`。这样可以避免 gate 刚通过时后端 `current_gate` 短暂滞后，导致 GateNav 高亮与右侧 Workbench 面板错位。
- `frontend/hooks/useAnalysis.ts` 继续保留有限的本地状态补丁，但范围被约束在“资产上传”和“metadata 绑定”两类会直接让 G2/G3 退回待确认态的动作；其余场景仍通过 query invalidation 回到后端 workflow 真相。
- `frontend/hooks/useManifest.ts` 不再在 QC 确认后做危险的 G3→G4 乐观推进，只刷新 `assets`、`manifest`、`workflow` 查询，等待后端 gates/workflow 给出真实推进结果。
- 2026-03-11：`frontend/components/gates/DraftPanel.tsx` 已完成 G5 第三阶段 refinement。当前面板按 system sections 渲染并用 latest draft 确定 section 分组（approved / needs-review / ready-to-generate）；draft preview 默认折叠，只有用户显式展开才展示内容，对无草稿或空内容 section 提供明确 unavailable / waiting 状态；review comments 会显示 decision markers；generate / approve / review 三类动作均使用 section-scoped local inline feedback，并在对应 section 的 authoritative refresh 后清理 success；G5 生成按钮使用单一优先级 disabled helper reason，顺序为：任务进行中 → 缺少 confirmed outline → 已有 latest draft → workflow blocker → fallback prerequisite。双模型审查后已额外修正：已有 latest draft / blocker 时按钮真实禁用、pending/error 不再跨 section 串味、success lifecycle 不再被无关 section 刷新误清除。

- 2026-03-11：OpenSpec `refine-g4-g5-workbench-and-minimal-acceptance` Phase 4/5 已全部落地。最小自动化验收基线采用 `Vitest + JSDOM + React Testing Library` 做 panel-level smoke，直接覆盖 `EvidenceMatrixPanel` 与 `DraftPanel`，不经过 MainShell 壳层。测试基础设施：`frontend/vitest.config.ts`（JSDOM 环境配置）、`frontend/vitest.setup.ts`（`@testing-library/jest-dom` matchers）、`frontend/components/gates/testUtils.tsx`（QueryClient provider wrapper）、`frontend/components/gates/testFixtures.ts`（contract-shaped fixture builders）。已验证的关键语义：(1) deterministic latest-selection（version-first, updatedAt-second）；(2) async truth split（202 Accepted ≠ artifact ready，websocket 可能缺失）。运行命令：`npm run test:smoke`。Playwright 仍保留为后续扩展路径。

## 前端边界

- `frontend/lib/api.ts` 只放通用 request wrapper
- `frontend/lib/query.ts` 只放 QueryClient/Provider
- `frontend/lib/websocket.ts` 只放底层 socket client
- 域内数据逻辑写入各 feature 自己的 hook
- 布局组件不发起数据请求，只接收 props

## 当前状态

- 系统工作台壳层已真实装配（非 placeholder）
- GateNav 基于真实 workflow snapshot 派生 gate 状态，并已补齐 mixed-case / snake_case 工作流响应兼容层
- EvidenceHub / GatePanel 不再只停留在空态映射：G4 的 `EvidenceMatrixPanel` 已支持 Evidence Matrix 生成、claim 审批、claim evidence-link 创建、outline 生成/确认、outline binding 展示与创建，以及可用 assets 展示；G5 的 `DraftPanel` 已支持 section draft 生成、review comments 展示、review comment 提交、draft 审批。
- 系统页 websocket invalidation 现在除 `workflow.state_changed` / `gate.passed` / `gate.blocked` 外，也会在 `task.succeeded` / `task.failed` 时刷新 workflow，避免异步任务结束后工作台信息滞后。
- 项目列表/详情页为独立页面，不经过 MainShell 套壳
- 已重新运行前端 `typecheck` 并通过，确认本轮 G1/G2/G3 接入恢复未引入类型回归

## 下一阶段承接原则

- 前端继续复用现有 MainShell / ProjectWorkspace / EvidenceHub / GatePanel / WorkflowPanel / StatusTray 结构与 workflow snapshot 数据流。
- Phase 2 重点不是重做壳层，而是在现有工作台中按 gate 逐步承接业务工件与操作面板。
- G0：嵌入 SystemDefinitionForm 编辑流（表单校验 + blocker 联动 + 乐观更新）。
- G1-G5：每个 gate 补操作面板（至少展示状态 + blocker + 按钮占位），不要求立即补完整编辑器。
- 现阶段 G4/G5 已具备最小可操作闭环，后续前端演进重点转为交互细化、批量操作、错误提示与更强的可视化反馈，而不是重新搭建壳层。
