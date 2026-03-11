# Team Research: 下一步应该要做什么（Phase 1.5 后）

## 增强后的需求

Phase 1.5（控制平面收口 / 系统主链打通）已完成，前端工作台装配已闭环。下一步研究目标是确定"最小业务闭环"应该优先落在哪些已有边界上，并输出限制解空间的约束集合。

用户已确认的推进方向：
- **实现范围**：G1-G3 前半链（Figure Plan 生成/确认、资产上传与 AnalysisRun、Manifest/资产确认）
- **编排深度**：先不扩 Temporal，保留当前 thin workflow / task event 模式
- **G1 生成时机**：Figure Plan 在 G1 阶段由用户手动触发异步生成，不作为 G0 `advance` 的隐式副作用
- **G2 资产绑定**：先采用手动显式绑定，不做自动映射或自动建议确认
- **Executor 策略**：下一阶段将 Claude / Vision / Python 三类 executor 一起纳入，而不是先用单类或全 mock 收口
- **文档更新**：研究文件落地后，使用 recorder agent 更新项目文档

## 约束集

### 硬约束

- [HC-1] 技术栈继续沿用当前已锁定方向：FastAPI + SQLAlchemy + Alembic + PostgreSQL + Redis + Temporal + MinIO + WebSocket，前端为 Next.js + React + React Query。不得在规划阶段引入新框架。— 来源：llmdoc / 代码库
- [HC-2] 当前目标仍是**单实验体系闭环 MVP**，不是整篇论文平台或多实验体系协同。— 来源：llmdoc / 用户
- [HC-3] 下一阶段优先落地 **G1-G3 前半链**，而不是先做 G4/G5 写作链或先做泛化任务系统。— 来源：用户
- [HC-4] Evidence Matrix 在 MVP 中直接由 `claims + claim_evidence_links` 承担事实表达，**不新增独立快照表或显式 `evidence_matrices` 实体**。— 来源：继续推进项目-research.md / 用户
- [HC-5] 第一批审批能力仅覆盖 **Section Draft 审批**，`approval_tasks` 在 MVP 首轮不得扩张到 Figure Plan、Manifest、Outline 等全工件审批。— 来源：继续推进项目-research.md / 用户
- [HC-6] `POST /systems/{id}/advance` 只表达推进请求，真正推进必须由 gates 校验 + workflow 决策完成，不能直接改状态。— 来源：llmdoc / gates.service
- [HC-7] 所有生成类动作必须异步执行并立即返回 `workflow_id` / `job_id` / `JobHandle`，不得同步返回最终产物。— 来源：llmdoc / api-contracts.md
- [HC-8] 固定门禁映射 G0–G5 与 `SystemState` / `GateRequirementKey` 枚举必须保留，不得自由改名或允许绕门禁跳步。— 来源：llmdoc / enums.py
- [HC-9] 业务真相必须留在数据库与 workflow，不在 executor，也不在前端。— 来源：llmdoc / backend-modules.md
- [HC-10] `claim_evidence_links` 现有两条部分唯一索引与 `analysis_run_id` 的删除限制语义必须保持：当 link 仍引用某个 `AnalysisRun` 时，数据库必须拒绝删除该 `AnalysisRun`。— 来源：data-models.md / evidence.py
- [HC-11] Manifest 必须继续作为独立、可版本化实体，不能并回 asset 或 system card。— 来源：llmdoc / manifest.py
- [HC-12] Draft 必须只基于已批准 claims 写作；即便当前服务层未完全实现，该约束在 plan 阶段也不能被降级为可选。— 来源：llmdoc / backend-modules.md
- [HC-13] 当前 `system_workflow.py` 仍为薄适配层，不承载真实长流程编排；下一阶段不扩 Temporal 重型编排，只要求生成动作真实异步化并能回写 workflow + WebSocket。— 来源：用户 / system_workflow.py
- [HC-14] Figure Plan 在 G1 阶段由用户手动触发异步生成，不作为 G0 `advance` 的隐式副作用。— 来源：用户
- [HC-15] G2 中上传资产与 Figure Plan 的绑定方式，首轮采用手动显式绑定，不做自动映射或自动建议确认。— 来源：用户
- [HC-16] 下一阶段 executor 范围明确包含 `ClaudeCodeExecutor`、`VisionExecutor`、`PythonAnalysisExecutor` 三类，不以 service 层全 mock 替代。— 来源：用户
- [HC-17] 后端实现顺序必须遵守现有层次：先 common/persistence 之上的业务模块，再 workflow/realtime，再 API 装配；不能把核心业务逻辑直接堆进 router 或 placeholder workflow。— 来源：backend-modules.md / 代码库
- [HC-18] G1/G2/G3 的 gate 前置条件已在 `gates.service.py` 中编码完成（`check_figure_plan_ready` / `check_data_and_analysis_ready` / `check_assets_confirmed`），下一阶段必须复用这些判定逻辑，不得重新发明。— 来源：gates.service.py
- [HC-19] 前端工作台已有双栏主视图（EvidenceHub 左栏 + GatePanel 右栏）与状态托盘（StatusTray），不应重做壳层；G1-G3 承接面应复用现有 hooks、panel、MainShell、ProjectWorkspace、StatusTray 数据流。— 来源：frontend-workbench.md / 代码库
- [HC-20] 前端不能自行决定 gate 是否可推进，只能消费 workflow snapshot / blocker / task event。— 来源：frontend-workbench.md / useProjectStatus.ts

### 软约束

- [SC-1] 延续 Document-Driven Development：任何后续实现前，优先阅读 `llmdoc/index.md`、`llmdoc/overview/*` 及相关 architecture/reference 文档。— 来源：系统规则 / llmdoc
- [SC-2] 继续使用当前公共契约：`ApiResponse`、`TaskEvent`、`JobHandle`、`Blocker`、`GateReview`、`WorkflowSnapshot`。— 来源：代码库 / common/schemas.py
- [SC-3] 前端当前仍是页面骨架与任务托盘壳层，因此下一阶段不应把前端页面完成度当作后端最小闭环的验收前提。— 来源：Gemini 前端约束探索
- [SC-4] `/ws/tasks` 仍作为长任务反馈主通道；即使当前只是 bootstrap + heartbeat 样例，也应保持此端点作为兼容边界。— 来源：llmdoc / websocket.py
- [SC-5] 继续沿用现有版本化与审计模式：核心工件通过 `version + audit fields` 提供可追溯基线。— 来源：data-models.md / persistence/models
- [SC-6] 当前阶段优先做最小可验证闭环，而不是提前抽象通用平台能力。— 来源：项目目标 / 用户选择
- [SC-7] G1-G3 前端承接面应尽量复用现有 `EvidenceHub` / `GatePanel` / `WorkflowPanel` / `StatusTray` 组件，只需补充对应 gate 的空态描述与下一步动作提示，不需要立即实现完整编辑器。— 来源：Gemini 前端约束探索 / 代码库

### 依赖关系

- [DEP-1] `common.enums/events/schemas` → `modules/* / workflows / realtime / api`：共享契约是所有后续实现的底层依赖。
- [DEP-2] `persistence/models + alembic` → `service/repository`：服务层必须以已存在 schema 和约束为边界，不能反向假设数据库结构。
- [DEP-3] `figure_plans + figure_plan_assets` → `assets + analysis_runs`：Figure Plan 定义数据需求，资产上传与分析必须与 Figure Plan 结构形成闭环。
- [DEP-4] `assets + asset_metadata` → `asset_manifests`：Manifest 生成依赖资产与元数据的完整性。
- [DEP-5] `workflow_instances/workflow_events` → `/systems/{id}/advance` 与生成动作：推进与生成必须留下可追溯 workflow 记录。
- [DEP-6] HTTP 任务创建接口 → WebSocket `TaskEvent` 输出：异步句柄与实时状态必须成对设计，否则会出现"有 job handle、无真实状态反馈"的假异步。
- [DEP-7] Docker Compose 基础设施 → 本地联调：PostgreSQL / Redis / MinIO / Temporal 是继续推进后端最小闭环的外部依赖。
- [DEP-8] `gates.service` 已编码的 G1/G2/G3 判定逻辑 → 下一阶段业务生成器：生成器必须确保生成的工件能通过对应 gate 的前置条件校验。
- [DEP-9] 前端 `useProjectStatus` / `useSystemAdvance` / `useWebSocket` → 后端 `/systems/{id}/workflow` / `/systems/{id}/advance` / `/ws/tasks`：前端数据流已接入真实后端端点，下一阶段后端生成器必须通过这些端点反馈状态。

### 风险

- [RISK-1] 将 llmdoc / README 中的 API 契约误判为已实现 API，会导致下一阶段计划漏算大量后端模块与路由落地工作。— 缓解：明确区分"已落地基础"和"规划契约"。
- [RISK-2] `backend/app/modules/assets` / `backend/app/modules/evidence` / `backend/app/modules/drafts` 目前仍为空包，若直接在 router 或 workflow 中堆逻辑，会破坏既定模块边界。— 缓解：按 `router/service/schemas/repository` 模板逐步补模块。
- [RISK-3] `system_workflow.py` 与 `broadcaster.py` 仍是 placeholder，过早暴露生成接口会形成"返回句柄但没有真实编排/广播"的假闭环。— 缓解：先做后端最小闭环中必要的 workflow / task / realtime 最小实现。
- [RISK-4] 当前测试主要覆盖 schema、契约和部分行为约束，尚未覆盖真实 gate 判定、workflow 推进与完整异步任务链路。— 缓解：后续计划必须显式包含这些测试补齐项。
- [RISK-5] 多张表同时保存 `project_id` 与 `system_id`，但缺少数据库级复合作用域校验，服务层若不主动校验，可能出现跨项目脏数据。— 缓解：把作用域一致性校验作为服务层硬要求。
- [RISK-6] G2 的 `check_data_and_analysis_ready` 当前只检查"有资产"和"有成功 AnalysisRun"，未校验资产是否与 Figure Plan 的 `data_needed_json` 对应。— 缓解：下一阶段补充 Figure Plan 与资产的映射校验逻辑。
- [RISK-7] 前端 G2 阶段已细分为 `Data_Pending` / `Data_Uploaded` / `Analysis_Ready` 子状态，但后端 `SystemState` 枚举也有这些状态，若前后端状态映射不一致，会导致 UI 与真实状态脱节。— 缓解：确保前后端状态枚举与 gate 判定逻辑一致。
- [RISK-8] 当前 `BaseExecutor` 只是占位实现，若下一阶段直接依赖 executor 返回真实结果，会形成"调用成功但无实际执行"的假闭环。— 缓解：三类 executor 一起纳入实现计划，但要严格限定为最小真实能力，避免横向过度扩张。
- [RISK-9] 前端 `StatusTray` 已接入真实 WebSocket，但若后端生成动作未真实推送 `TaskEvent`，用户会看到"任务创建成功但无进度反馈"的断层体验。— 缓解：确保生成动作在 workflow 记录后立即通过 broadcaster 推送事件。
- [RISK-10] 三类 executor 同步纳入会扩大下一阶段实施面，若缺少文件隔离和依赖拆分，容易让 team-plan 失去并行性。— 缓解：后续 team-plan 必须按 executor / service / router / frontend 承接面做严格文件分层。

## 成功判据

- [OK-1] 本地基线不被破坏：基础设施可启动、Alembic 可升级、FastAPI 可启动、`/ws/tasks` 可连接。
- [OK-2] 存在一个后端最小闭环，能围绕单实验体系推进 G1-G3 核心状态，而不是只有空路由和占位 workflow。
- [OK-3] `/systems/{id}/advance` 在门禁不满足时返回结构化 blocker / review 信息，而不是直接修改系统状态。
- [OK-4] 当满足条件时，推进动作会留下可追溯的 `workflow_instances` 与 `workflow_events` 记录。
- [OK-5] 生成类动作表现为"立即返回 `JobHandle`，随后通过 WebSocket 推送任务状态变化"。
- [OK-6] G1 阶段：Figure Plan 生成动作能真实创建 `figure_plans` 记录，并通过 `check_figure_plan_ready` 校验后推进至 G2。
- [OK-7] G2 阶段：资产上传能真实创建 `assets` 记录，分析动作能真实创建 `analysis_runs` 记录，并通过 `check_data_and_analysis_ready` 校验后推进至 G3。
- [OK-8] G3 阶段：Manifest 生成能真实创建 `asset_manifests` 记录，资产元数据能真实创建 `asset_metadata` 记录，并通过 `check_assets_confirmed` 校验后推进至 G4。
- [OK-9] 前端 EvidenceHub 能根据当前 gateKey 和 currentState 渲染对应的空态描述与下一步动作提示。
- [OK-10] 前端 GatePanel 能根据当前 gateKey 和 gateVisualState 渲染对应的工作区空态与操作提示。
- [OK-11] 前端 StatusTray 能实时展示 AnalysisRun 等异步任务进度，并在任务完成后触发 workflow 失效刷新。
- [OK-12] 新实现不破坏现有 `ApiResponse`、`TaskEvent`、`JobHandle`、迁移与模型测试基线。

## 开放问题（已解决）

- Q1: 下一阶段首先落地哪条主链路？ → A: G1-G3 前半链 → 约束：[HC-3]
- Q2: 下一阶段是否把 Temporal 真实长流程一起纳入重点？ → A: 先不扩 Temporal → 约束：[HC-13]
- Q3: 研究文件落地后，要不要顺手同步项目文档？ → A: 更新项目文档 → 后续动作：使用 recorder agent 更新 llmdoc
- Q4: G1 的 Figure Plan 生成时机？ → A: G1 阶段由用户手动触发异步生成 → 约束：[HC-14]
- Q5: G2 中上传资产与 Figure Plan 的绑定方式？ → A: 手动显式绑定 → 约束：[HC-15]
- Q6: 下一阶段 executor 的落地策略？ → A: Claude / Vision / Python 三类一起做 → 约束：[HC-16]

## Gemini 前端约束探索摘要

来源：Gemini 前端约束探索（2026-03-07）

**已有结构**：
- MainShell & ProjectWorkspace: 已实现基于槽位的双栏布局（EvidenceHub 居左, Workbench 居右）
- GateNav: 6 阶段门禁导航（G0-G5），已接入真实 snapshot 派生的视觉状态（passed/active/locked/neutral）
- StatusTray: 已接入真实 WebSocket 任务流，支持实时展示 AnalysisRun 等异步任务进度
- EvidenceHub & GatePanel: 已建立基于 gateKey 和 currentState 的内容映射逻辑（空态描述与 Blocker 提示）

**已有规范**：
- Blocker-Driven UI: 前端不自行判定推进条件，通过消费 snapshot.latestBlockers 进行用户引导
- Real-time Invalidation: 监听 WebSocket 事件（workflow.state_changed）触发 React Query 失效以刷新状态
- Slot-based Layout: 左栏 EvidenceHub 面板服务于"证据/资产上下文"，右栏 GatePanel 面板承载"当前门禁操作"
- Gate-Substate Mapping: G2 阶段在前端已细分为 Data_Pending/Data_Uploaded/Analysis_Ready 子状态

**约束发现**：
- 单实验闭环优先: 下一阶段应优先补齐 G1 (Figure Plan) 到 G3 (Asset Confirmation) 的实验资产管理闭环
- 推进权限约束: 前端仅负责发送 /advance 请求，推进失败时需解析并展示后端返回的结构化 blockers
- 资产映射依赖: G2 的数据上传界面必须与 G1 定义的 Figure Plan 结构（data_needed）在交互上形成闭环
- 双面板隔离: 所有编辑/输入操作需限制在 Workbench（右栏）内，EvidenceHub（左栏）保持只读或筛选状态

**开放问题**：
- Figure Plan 生成时机: 是在 G0 通过后由后端异步自动触发生成，还是需要在 G1 界面由用户点击"生成"按钮？
- 资产与图表绑定: G2 上传后的资产如何与 Figure Plan 自动或手动映射？前端是否需要提供绑定交互？
- G4/G5 的范围: 最小闭环是否包含 Evidence Matrix (G4) 与 Draft (G5)？（本分析建议先聚焦 G1-G3 实验闭环）

**依赖**：
- Backend CRUD: 需要后端提供 FigurePlan 的获取与确认接口（G1 阻塞点）
- Asset Upload API: 需要稳定的文件上传并触发 AnalysisRun 的端点（G2 阻塞点）
- Manifest API: 需要获取并确认 AssetManifest 的接口（G3 阻塞点）

**风险**：
- G2 长任务体验: 分析任务可能耗时较长，若 StatusTray 与 GatePanel 反馈不同步，用户可能对状态产生疑惑
- 版本控制冲突: FigurePlan 和 Outline 均有 version 字段，前端并发编辑时需考虑版本冲突处理

**成功判据提示**：
- G1: EvidenceHub 渲染出真实的 Figure Plan 列表；Workbench 提供确认按钮，点击后 Advance 成功进入 G2
- G2: Workbench 提供上传组件；上传成功后 StatusTray 自动出现 AnalysisRun 进度；分析成功后 Blocker 消失
- G3: EvidenceHub 展示 Asset Manifest；Workbench 提供确认操作，点击后 Advance 进入 G4

## 后端约束探索摘要（代替 Codex）

来源：手动代码库分析（2026-03-07）

**已有结构**：
- `gates.service.py` 已编码 G0-G5 全部 gate 判定逻辑，包括 `check_figure_plan_ready` / `check_data_and_analysis_ready` / `check_assets_confirmed`
- `systems.service.py` 已实现 `advance_system` 主控流程：gate review → blocked/passed 分支 → workflow 记录 → broadcaster 推送
- `tasks.service.py` 已实现 `TaskWorkflowService`：workflow 实例创建、事件追加、snapshot 构建
- `system_workflow.py` 仍为薄适配层，只提供 `start_system_workflow` / `append_system_workflow_event` 包装
- `broadcaster.py` 已实现进程内 pub/sub，支持多订阅者独立队列与自动清理
- `websocket.py` 已实现 `/ws/tasks` 端点，支持真实事件推送
- `persistence/models` 已落地全部核心表：`figure_plans` / `figure_plan_assets` / `assets` / `asset_metadata` / `asset_manifests` / `analysis_runs` / `claims` / `claim_evidence_links` / `outlines` / `outline_asset_bindings` / `section_drafts` / `review_comments` / `workflow_instances` / `workflow_events` / `approval_tasks`

**已有规范**：
- 模块模板：`router.py` / `service.py` / `schemas.py` / `repository.py` / `__init__.py`
- 公共契约：`ApiResponse` / `TaskEvent` / `JobHandle` / `Blocker` / `GateReview` / `WorkflowSnapshot`
- 版本化与审计：核心工件通过 `version + audit fields` 提供可追溯基线
- 异步边界：生成类动作必须立即返回 `JobHandle`，随后通过 WebSocket 推送任务状态变化

**约束发现**：
- G1-G3 gate 判定逻辑已编码完成，下一阶段必须复用这些判定逻辑，不得重新发明
- `backend/app/modules/assets` / `backend/app/modules/evidence` / `backend/app/modules/drafts` 目前仍为空包，是最直接缺口
- 当前 `BaseExecutor` 只是占位实现，若下一阶段直接依赖 executor 返回真实结果，会形成"调用成功但无实际执行"的假闭环
- 后端实现顺序必须遵守现有层次：先 common/persistence 之上的业务模块，再 workflow/realtime，再 API 装配

**开放问题**：
- Figure Plan 生成时机: 是在 G0 通过后由后端异步自动触发生成，还是需要在 G1 界面由用户点击"生成"按钮？
- 资产与图表绑定: G2 上传后的资产如何与 Figure Plan 自动或手动映射？是否需要在 service 层补充映射逻辑？
- Executor 真实实现: 下一阶段是否需要补充 `ClaudeCodeExecutor` / `VisionExecutor` / `PythonAnalysisExecutor` 的真实实现，还是先在 service 层 mock？

**依赖**：
- `figure_plans + figure_plan_assets` → `assets + analysis_runs`：Figure Plan 定义数据需求，资产上传与分析必须与 Figure Plan 结构形成闭环
- `assets + asset_metadata` → `asset_manifests`：Manifest 生成依赖资产与元数据的完整性
- `workflow_instances/workflow_events` → `/systems/{id}/advance` 与生成动作：推进与生成必须留下可追溯 workflow 记录

**风险**：
- G2 的 `check_data_and_analysis_ready` 当前只检查"有资产"和"有成功 AnalysisRun"，未校验资产是否与 Figure Plan 的 `data_needed_json` 对应
- 当前 `system_workflow.py` 仍为薄适配层，不承载真实长流程编排；若下一阶段过早暴露生成接口，会形成"返回句柄但没有真实编排/广播"的假闭环
- 前端 G2 阶段已细分为 `Data_Pending` / `Data_Uploaded` / `Analysis_Ready` 子状态，但后端 `SystemState` 枚举也有这些状态，若前后端状态映射不一致，会导致 UI 与真实状态脱节

**成功判据提示**：
- G1 阶段：Figure Plan 生成动作能真实创建 `figure_plans` 记录，并通过 `check_figure_plan_ready` 校验后推进至 G2
- G2 阶段：资产上传能真实创建 `assets` 记录，分析动作能真实创建 `analysis_runs` 记录，并通过 `check_data_and_analysis_ready` 校验后推进至 G3
- G3 阶段：Manifest 生成能真实创建 `asset_manifests` 记录，资产元数据能真实创建 `asset_metadata` 记录，并通过 `check_assets_confirmed` 校验后推进至 G4
