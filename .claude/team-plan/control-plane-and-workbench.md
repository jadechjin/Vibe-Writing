# Team Plan: control-plane-and-workbench

## 概述

在模型、迁移、公共契约和前后端骨架已经落地的前提下，本轮不再重复扩表或继续堆 placeholder，而是优先打通“真实控制平面 + 前端工作台基础”。

根据最新确认，本阶段正式收敛为：

> **Phase 1.5：控制平面收口 / 系统主链打通**

目标不是新增业务模块，而是让已有 MVP 从“模块存在”变成“流程真实”。

本轮最小可验证闭环：

`创建项目 → 创建实验体系 → 更新体系定义 → advance 触发门禁评审 → 写入 workflow/task 事件 → /ws/tasks 推送 → 前端 StatusTray / Workspace 消费`

## 当前基线

- 后端已有统一响应/错误基线、SQLAlchemy 模型与迁移、执行器契约、FastAPI 启动壳层。
- 前端已有 Next.js 布局壳层、项目/体系页面占位、React Query 基线、底层 WebSocket client。
- 当前主要缺口不是数据层，而是 `HTTP -> service -> gate review -> workflow records -> realtime -> frontend` 这条主链尚未接通。

## Codex 分析摘要

- 现有模型和公共契约已经足够支撑第一轮真实实现，不需要先改迁移基线。
- 当前瓶颈集中在 `backend/app/api/router.py` 空壳、`backend/app/workflows/system_workflow.py` 占位、`backend/app/realtime/broadcaster.py` 为 no-op、`backend/app/api/websocket.py` 仍在伪造 bootstrap/heartbeat。
- 推荐优先落地的真实后端能力是：`POST /projects`、`GET /projects/{id}`、`POST /projects/{id}/systems`、`PATCH /systems/{id}`、`POST /systems/{id}/advance`、`GET /systems/{id}/workflow`。
- 不推荐先铺 Figure Plan / Evidence / Draft 生成接口；在 workflow 与 realtime 仍为占位时，这会制造“有 job_id、无真实反馈”的假异步。
- 建议让 `gates` 只负责“过不过、为什么”，`workflow/tasks` 只负责“推进到哪、记录什么事件”，并先用单进程内存 broadcaster 完成 MVP 级实时链路。

## Gemini 分析摘要

- 前端应采用门禁驱动的双栏工作区：顶部 `G0–G5` 导航，中部左栏 Evidence Hub，中部右栏 Gate 对应工作区，底部 StatusTray。
- 当前前端第一优先级不是补全所有内容编辑器，而是把布局、路由分发、状态托盘和异步反馈流做成真能力。
- 域内逻辑应放在 feature hooks；`frontend/lib/api.ts` 只做通用请求包装，`frontend/lib/websocket.ts` 只做底层 socket client。
- 所有生成/推进动作都应立即落到 StatusTray，由 WebSocket 事件驱动 React Query 失效和 UI 刷新，不能同步等待最终产物。

## 技术方案

1. **后端先打控制平面，Temporal 先保持薄适配层**
   - 不把业务真相塞进 workflow adapter。
   - `advance` 只表达推进请求，真实推进由 `gates.service` + `tasks.service` 决定。

2. **维持单一职责边界**
   - `backend/app/api/router.py`、`backend/app/main.py` 只做装配。
   - `projects/systems` 模块处理 HTTP 与业务编排。
   - `gates` 只产出 `GateReview/Blocker`。
   - `tasks` 只负责 `JobHandle`、`WorkflowInstance`、`WorkflowEvent` 与事件广播。

3. **先使用 MVP 级 broadcaster，后续再升级总线**
   - 本轮采用进程内发布/订阅，支撑本地单实例开发。
   - 后续如需多实例，再升级到 Redis/pubsub。

4. **前端先做工作台外壳与异步反馈，不抢跑完整业务面板**
   - 先把 GateNav、MainShell、StatusTray、项目/体系路由分发做成真页面。
   - Evidence Hub 与右侧 Workbench 先接工作流状态与空态，不直接承诺完整 Figure Plan / Draft 编辑器。

5. **控制平面需要一个实现型补充接口**
   - 为了替换 `frontend/app/projects/page.tsx` 占位页，本轮补充 `GET /projects` 作为实现型扩展接口。
   - 这不改变核心业务不变式，只是补足前端入口页所需读取能力。

## 完成状态

> **最后更新：** 2026-03-07

### 已完成的任务

| Task | 状态 | 说明 |
|------|------|------|
| Task 1: Projects 控制平面接口 | 已完成 | POST/GET /projects, GET /projects/{id} |
| Task 2: Gates 评审核心 | 已完成 | resolve_active_gate, review_gate, 结构化 Blocker |
| Task 3: Tasks / Workflow 持久化服务 | 已完成 | workflow instance/event CRUD |
| Task 4: 实时广播与 WebSocket 通道 | 已完成 | 进程内 broadcaster + /ws/tasks 真实事件 |
| Task 5: Systems 接口与 advance 编排 | 已完成 | create/update/advance/workflow 全部落地 |
| Task 6: 应用装配与生命周期注入 | 已完成 | router.py 注册, lifespan broadcaster |
| Task 7: 前端壳层与 Gate 导航 | 已完成 | GateNav/MainShell/ProjectWorkspace |
| Task 8: WebSocket hook 与 StatusTray | 已完成 | useWebSocket + StatusTray + TaskItem |
| Task 9: 前端控制平面客户端与路由页 | 已完成 | 项目列表/详情页、hooks、api wrapper |
| Task 10: Evidence Hub 与 Gate 工作区空态面板 | 已完成 | EvidenceHub + GatePanel + WorkflowPanel |

### 装配修复（本轮）

Task 10 生成 EvidenceHub / GatePanel / WorkflowPanel 后，这些面板最初没有真实挂载到系统页。本轮修复内容：

1. **根 layout 去壳** — `frontend/app/layout.tsx` 不再无条件把所有页面包进 MainShell，只保留 `<Providers>{children}</Providers>`，避免项目列表页/详情页被错误套壳。
2. **系统页真实装配** — `frontend/app/projects/[projectId]/systems/[systemId]/page.tsx` 显式导入并组装 EvidenceHub、GatePanel、StatusTray，通过 props 注入 MainShell 的 evidencePanel / workbenchPanel / statusTray 槽位。
3. **GateNav 基于真实数据** — 系统页通过 `useProjectStatus` 获取 workflow snapshot，调用 `deriveGateItems` 派生出真实的 gate 状态（passed/active/locked），传入 MainShell 的 `gates` prop。
4. **项目列表/详情页独立** — `projects/page.tsx` 和 `projects/[projectId]/page.tsx` 保持独立页面样式，不经过 MainShell 包裹。

## 子任务列表

### Task 1: Projects 控制平面接口
- **类型**: 后端
- **文件范围**:
  - `backend/app/modules/projects/__init__.py`
  - `backend/app/modules/projects/schemas.py`
  - `backend/app/modules/projects/repository.py`
  - `backend/app/modules/projects/service.py`
  - `backend/app/modules/projects/router.py`
  - `backend/tests/modules/projects/test_projects_api.py`
- **依赖**: 无
- **实施步骤**:
  1. 定义项目创建、列表、详情的 schema。
  2. 实现 `create_project`、`list_projects`、`get_project_detail` repository/service/router。
  3. 统一返回 `ApiResponse`，详情接口附带体系摘要信息。
  4. 补 pytest 覆盖创建、列表、详情场景。
- **验收标准**:
  - `POST /projects`、`GET /projects`、`GET /projects/{id}` 返回真实数据库结果。
  - 项目详情可被前端入口页直接消费。

### Task 2: Gates 评审核心
- **类型**: 后端
- **文件范围**:
  - `backend/app/modules/gates/__init__.py`
  - `backend/app/modules/gates/schemas.py`
  - `backend/app/modules/gates/service.py`
  - `backend/tests/modules/gates/test_gate_review.py`
- **依赖**: 无
- **实施步骤**:
  1. 实现 `resolve_active_gate`、`review_gate`。
  2. 实现 `check_system_defined`、`check_figure_plan_ready`、`check_data_and_analysis_ready`、`check_assets_confirmed`、`check_evidence_and_outline_ready`、`check_chapter_approved`。
  3. 所有失败都返回结构化 `Blocker`，不抛散乱字符串错误。
  4. 以当前事实表为依据编写 gate review 测试。
- **验收标准**:
  - 固定门禁映射保持不变。
  - 门禁失败时 `advance` 上游可直接消费结构化 blocker。

### Task 3: Tasks / Workflow 持久化服务
- **类型**: 后端
- **文件范围**:
  - `backend/app/modules/tasks/__init__.py`
  - `backend/app/modules/tasks/schemas.py`
  - `backend/app/modules/tasks/repository.py`
  - `backend/app/modules/tasks/service.py`
  - `backend/app/workflows/system_workflow.py`
  - `backend/tests/modules/tasks/test_task_workflow_service.py`
- **依赖**: 无
- **实施步骤**:
  1. 实现 workflow instance/event 的创建、追加、查询。
  2. 实现统一 `JobHandle` 生成与 task/workflow 标识对齐。
  3. 让 `system_workflow.py` 保持薄适配层，不承载业务真相。
  4. 为事件留痕与 workflow 快照补测试。
- **验收标准**:
  - 成功推进或阻塞都能写入 workflow 留痕。
  - `GET /systems/{id}/workflow` 所需快照可从 service 直接获得。

### Task 4: 实时广播与 WebSocket 通道
- **类型**: 后端
- **文件范围**:
  - `backend/app/realtime/__init__.py`
  - `backend/app/realtime/broadcaster.py`
  - `backend/app/api/websocket.py`
  - `backend/tests/realtime/test_task_broadcaster.py`
- **依赖**: Task 3
- **实施步骤**:
  1. 在 broadcaster 中实现进程内 `publish / subscribe / unsubscribe`。
  2. 让 `/ws/tasks` 只转发真实 `TaskEvent`，移除伪造 bootstrap/heartbeat 逻辑。
  3. 处理连接断开、订阅清理与异常关闭。
  4. 补充 WebSocket 广播测试。
- **验收标准**:
  - 已发布的 `task.created / task.progress / task.succeeded / task.failed` 可被客户端收到。
  - 断开连接不会泄漏订阅状态。

### Task 5: Systems 接口与 advance 编排
- **类型**: 后端
- **文件范围**:
  - `backend/app/modules/systems/__init__.py`
  - `backend/app/modules/systems/schemas.py`
  - `backend/app/modules/systems/repository.py`
  - `backend/app/modules/systems/service.py`
  - `backend/app/modules/systems/router.py`
  - `backend/tests/modules/systems/test_systems_api.py`
- **依赖**: Task 1, Task 2, Task 3
- **实施步骤**:
  1. 实现 `create_system`、`update_system_definition`、`advance_system`、`get_workflow_snapshot`。
  2. 在 `advance_system` 中调用 gate review，并在同事务内更新 system/workflow 状态。
  3. 推进成功时生成 `JobHandle` 并写 workflow event；阻塞时返回结构化 blocker。
  4. 补 API 与服务测试。
- **验收标准**:
  - `POST /projects/{id}/systems`、`PATCH /systems/{id}`、`POST /systems/{id}/advance`、`GET /systems/{id}/workflow` 全部落地。
  - 未满足门禁时返回结构化 blocker，满足时写入 workflow 记录并触发 task 事件。

### Task 6: 应用装配与生命周期注入
- **类型**: 后端
- **文件范围**:
  - `backend/app/api/router.py`
  - `backend/app/main.py`
  - `backend/tests/api/test_app_bootstrap.py`
- **依赖**: Task 1, Task 4, Task 5
- **实施步骤**:
  1. 在 `api/router.py` 中注册 projects/systems routers。
  2. 在 `main.py` 的 lifespan 中初始化并注入 broadcaster。
  3. 确保异常处理、HTTP 路由与 WebSocket 路由协同工作。
  4. 补应用启动与路由注册测试。
- **验收标准**:
  - FastAPI 应用启动后能同时提供真实 HTTP API 与 `/ws/tasks`。
  - `router.py`、`main.py` 仍保持装配职责，不混入业务逻辑。

### Task 7: 前端壳层与 Gate 导航
- **类型**: 前端
- **文件范围**:
  - `frontend/app/layout.tsx`
  - `frontend/components/layout/MainShell.tsx`
  - `frontend/components/layout/GateNav.tsx`
  - `frontend/components/layout/ProjectWorkspace.tsx`
- **依赖**: 无
- **实施步骤**:
  1. 把当前简单 header 升级为固定 Gate 导航。
  2. 实现双栏工作区壳层：左 Evidence Hub 槽位，右 Workbench 槽位，底部状态托盘槽位。
  3. 为不同 gate 状态提供 `locked / active / passed / pending` 视觉状态。
  4. 保持布局组件只负责结构，不承载数据请求。
- **验收标准**:
  - 前端不再只有 placeholder header，而是形成可承载业务面板的稳定布局骨架。
  - Gate 导航可接收状态数据并渲染不同视觉状态。

### Task 8: WebSocket hook 与 StatusTray
- **类型**: 前端
- **文件范围**:
  - `frontend/lib/websocket.ts`
  - `frontend/hooks/useWebSocket.ts`
  - `frontend/components/tasks/StatusTray.tsx`
  - `frontend/components/tasks/TaskItem.tsx`
- **依赖**: Task 4, Task 7
- **实施步骤**:
  1. 为底层 socket client 增加事件解析与重连策略约束。
  2. 实现 `useWebSocket`，维护与当前 project/system 相关的任务流。
  3. 让 `StatusTray` 渲染任务列表、状态、进度与消息。
  4. 在事件到达时触发上层 query invalidation 回调，不显示全局阻塞遮罩。
- **验收标准**:
  - WebSocket 真实事件能在托盘中增量展示。
  - 前端能区分 `queued / running / waiting_user / succeeded / failed / cancelled`。

### Task 9: 前端控制平面客户端与路由页
- **类型**: 前端
- **文件范围**:
  - `frontend/lib/api.ts`
  - `frontend/hooks/useProjects.ts`
  - `frontend/hooks/useProjectStatus.ts`
  - `frontend/hooks/useSystemAdvance.ts`
  - `frontend/app/projects/page.tsx`
  - `frontend/app/projects/[projectId]/page.tsx`
  - `frontend/app/projects/[projectId]/systems/[systemId]/page.tsx`
- **依赖**: Task 5, Task 7, Task 8
- **实施步骤**:
  1. 实现通用 request wrapper，统一消费 `ApiResponse`。
  2. 实现项目列表/详情、体系创建、workflow 查询、advance 请求的 hooks。
  3. 替换 projects 与 project/system 页面 placeholder。
  4. 在体系页把 Gate 状态、workflow 快照与 advance 操作接到真实 API。
- **验收标准**:
  - 用户可在 UI 中创建项目、进入项目页、创建体系并查看 workflow 快照。
  - 体系页能真实发起 `advance`，并与 StatusTray 联动。

### Task 10: Evidence Hub 与 Gate 工作区空态面板
- **类型**: 前端
- **文件范围**:
  - `frontend/components/evidence/EvidenceHub.tsx`
  - `frontend/components/evidence/EmptyEvidenceState.tsx`
  - `frontend/components/gates/GatePanel.tsx`
  - `frontend/components/drafting/WorkflowPanel.tsx`
- **依赖**: Task 9
- **实施步骤**:
  1. 用左栏 Evidence Hub 承接资产/证据空态与未来入口。
  2. 右栏根据当前 gate 渲染 `System Definition / Upload Pending / Evidence Pending / Draft Pending / Approval Pending` 等工作区空态。
  3. 将 workflow snapshot 与 blocker 信息映射成用户可理解的界面文案。
  4. 确保这些面板不抢跑完整编辑器，只呈现当前阶段真实状态与下一步动作。
- **验收标准**:
  - `frontend/app/projects/[projectId]/systems/[systemId]/page.tsx` 不再是纯文本 placeholder，而是可操作的工作台。
  - 工作区空态严格与 gate/workflow 真实状态一致。

## 文件冲突检查

✅ 已按单 owner 拆分热点文件：

- `backend/app/api/router.py`、`backend/app/main.py` 仅归 Task 6。
- `backend/app/api/websocket.py`、`backend/app/realtime/*` 仅归 Task 4。
- `frontend/app/layout.tsx`、`frontend/components/layout/MainShell.tsx` 仅归 Task 7。
- `frontend/lib/websocket.ts` 仅归 Task 8。
- `frontend/lib/api.ts` 与 `frontend/app/projects/**` 仅归 Task 9。

## 并行分组

- **Layer 1（并行，建议 4 个 Builder）**: Task 1, Task 2, Task 3, Task 7
- **Layer 2（并行）**: Task 4, Task 5
- **Layer 3（并行）**: Task 6, Task 8
- **Layer 4（串行）**: Task 9
- **Layer 5（串行）**: Task 10

## 验证清单

- `POST /projects`、`GET /projects`、`GET /projects/{id}` 可真实读写数据库。
- `POST /projects/{id}/systems`、`PATCH /systems/{id}`、`POST /systems/{id}/advance`、`GET /systems/{id}/workflow` 全部可用。
- `/systems/{id}/advance` 在门禁不满足时返回结构化 blocker。
- workflow instance/event 持久化与系统状态推进保持同事务一致性。
- `/ws/tasks` 发送真实任务状态事件，不再伪造 bootstrap/heartbeat。
- 前端 StatusTray 能实时显示任务状态变化。
- 项目页与体系页不再是 placeholder，可驱动本轮控制平面闭环。

## 风险与注意事项

- `ExperimentalSystem.status` 与 `WorkflowInstance.current_state` 需要同事务更新，避免双真相漂移。
- 进程内 broadcaster 只适合本地单实例 MVP，后续多实例时需要替换为真正消息总线。
- `advance` 的返回模型需要在系统模块中一次性定清，避免同时返回 handle 与 blocker 时失去类型稳定性。
- 本轮只做工作台与控制平面，不宣称已完成 Figure Plan / Evidence Matrix / Outline / Draft 的完整业务闭环。
