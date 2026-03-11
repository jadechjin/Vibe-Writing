# Team Research: 推进计划评估

## 增强后的需求

评估用户提出的推进计划"先补 G0 可操作性 → 再补 G1/G4/G5 后端 API → 再补前端真实工作台 → 最后收敛 workflow 事件语义"的可行性、合理性与缺失项。

- **评估基线**：双视角并列——同时对照 llmdoc 已确认的"Phase 1.5 后优先 G1-G3 前半链"路线与用户新计划。
- **G2/G3 处理**：用户计划原文只列了 G1/G4/G5 后端 API，但 G2/G3 仍有未闭合缺口，需一并补入。
- **G0 目标**：在系统工作台页 GatePanel 嵌入 SystemDefinitionForm 组件，提供完整编辑流（表单校验 + blocker 联动 + PATCH API 调用）。
- **技术约束**：不引入新框架，不扩 Temporal 为真实长流程。

## 约束集

### 硬约束

- [HC-1] **后端 G0 能力已就绪**：`PATCH /systems/{id}` 已实现（`backend/app/modules/systems/router.py:40-50`），`SystemUpdateRequest` 已包含全部 G0 字段（`schemas.py:40-57`）。G0 缺口纯在前端。— 来源：代码实证
- [HC-2] **G0 gate 校验是硬规则**：`gates/service.py:64-92` 检查 6 个字段（research_goal / samples_subjects / variables_controls / output_metrics / methods_summary / system_card_json），缺任何一个都会返回 `system_definition_incomplete` blocker。— 来源：代码实证
- [HC-3] **llmdoc 已确认的下一阶段优先级是 G1-G3 前半链**（`llmdoc/overview/product.md`, `workflow-summary.md`, `repository-status.md`）。用户计划将此改为 G0-first + G1/G4/G5，需注意这是对既定文档路线的显式调整。— 来源：llmdoc
- [HC-4] **evidence / drafts 模块仍为空包**（各只有 `__init__.py`）。G4/G5 后端 API 的前提是先补这两个模块的 service/router/schemas/repository。— 来源：代码实证
- [HC-5] **api/router.py 目前只 include 了 projects/systems/assets**（`router.py:1-11`）。新增任何模块 API 都需要在此处显式注册。— 来源：代码实证
- [HC-6] **前端创建 system 只收 title + researchGoal**（`frontend/app/projects/[projectId]/page.tsx:219-230`）。CreateSystemInput 类型定义虽已包含全部字段（`useProjects.ts:43-51`），但 UI 只用了两个。— 来源：代码实证
- [HC-7] **前端没有 useUpdateSystem hook**。目前不存在调用 `PATCH /systems/{id}` 的前端 hook。补 G0 编辑流的前提是先建这个 hook。— 来源：代码实证
- [HC-8] **固定门禁映射 G0-G5 与 SystemState 枚举不可变**。任何实现都不能改名或跳步。— 来源：llmdoc + `继续推进项目-research.md` [HC-8]
- [HC-9] **所有生成类动作必须异步返回 JobHandle**。Figure Plan、Evidence Matrix、Outline、Section Draft 的 API 都必须遵守此规则。— 来源：llmdoc + `继续推进项目-research.md` [HC-7]
- [HC-10] **Evidence Matrix 在 MVP 中由 claims + claim_evidence_links 表达**，不新增独立表。— 来源：`继续推进项目-research.md` [HC-4]
- [HC-11] **第一批审批能力仅覆盖 Section Draft**。— 来源：`继续推进项目-research.md` [HC-5]
- [HC-12] **业务模块实现顺序**：先 common/persistence 之上的 service/repository，再 workflow/realtime 适配，再 API router 装配。不直接在 router 里堆核心逻辑。— 来源：llmdoc + `继续推进项目-research.md` [HC-14]
- [HC-13] **Draft 只能基于已批准 claims**。即便服务层未实现，该约束在计划阶段也不可降级为可选。— 来源：llmdoc 核心不变式
- [HC-14] **claim_evidence_links 的两条部分唯一索引与 analysis_run_id 删除限制语义必须保持**。— 来源：data-models.md + `继续推进项目-research.md` [HC-10]

### 软约束

- [SC-1] 前端当前工作台壳层（MainShell / GatePanel / EvidenceHub / StatusTray）不需要重做，继续复用。新增内容以组件注入方式嵌入现有槽位。— 来源：llmdoc frontend-workbench.md
- [SC-2] G0 编辑表单应在 GatePanel 的 G0 active 状态下条件渲染，并与 blocker 信息联动高亮缺失字段。— 来源：用户选择（系统页编辑流）
- [SC-3] 继续沿用现有公共契约：ApiResponse / TaskEvent / JobHandle / Blocker / GateReview / WorkflowSnapshot。— 来源：`继续推进项目-research.md` [SC-2]
- [SC-4] 前端 useProjectStatus 每 10 秒轮询 + WebSocket invalidation 的数据流不变。— 来源：代码实证（`useProjectStatus.ts:158`）
- [SC-5] Data_Pending 状态在当前代码中没有明确生产点，更像预留态。后续 G2 实现时需决定是否激活或移除。— 来源：用户分析

### 依赖关系

- [DEP-1] G0 前端编辑流 → `PATCH /systems/{id}` 后端接口（已存在）
- [DEP-2] G0 前端编辑流 → 新增 `useUpdateSystem` hook（不存在，需创建）
- [DEP-3] G1 后端 API → evidence 模块补齐（FigurePlan service/router/schemas）
- [DEP-4] G2 后端 API → assets 模块补充 AnalysisRun 业务入口（当前 gate 查的是 AnalysisRun 表，但没有创建 AnalysisRun 的 API）
- [DEP-5] G3 后端 API → assets 模块补充资产确认/QC 审核入口
- [DEP-6] G4 后端 API → evidence 模块（Claims + ClaimEvidenceLink CRUD）+ drafts 模块（Outline service/router）
- [DEP-7] G5 后端 API → drafts 模块（SectionDraft + ReviewComment + approval_tasks）
- [DEP-8] 所有生成类 API → workflow/realtime 适配层（当前仍是薄 placeholder）
- [DEP-9] 前端真实工作台 → 对应后端 API 全部落地

### 风险

- [RISK-1] **计划与 llmdoc 优先级不一致**：llmdoc 明确说"Phase 1.5 后优先 G1-G3 前半链"，用户计划把 G0 放首位并跳到 G4/G5。如果不同步更新 llmdoc，后续 Builder 会产生优先级混淆。— 缓解：研究结论中明确标注偏差，后续 plan 阶段同步更新 llmdoc。
- [RISK-2] **G2/G3 缺口被遗漏**：用户原计划只列了 G1/G4/G5，但 G2 缺少 AnalysisRun API、G3 缺少资产确认/QC 审核 API。如果跳过 G2/G3 直接做 G4/G5，gate 校验会卡死在 G2/G3。— 缓解：用户已确认补入 G2/G3 缺口。
- [RISK-3] **G4/G5 后端模块工作量远超 G0-G3**：evidence + drafts 两个模块目前完全为空，需从 repository → service → schemas → router 逐层搭建。而 G0 只需前端约 3-5 个文件改动。工作量分布极不均匀。— 缓解：在 plan 阶段按模块拆 Builder 任务，分层并行。
- [RISK-4] **workflow event 双重记录**：`systems/service.py` 的 `_handle_gate_blocked` / `_handle_gate_passed` 先 `start_system_workflow` 创建初始事件，再 `record_gate_blocked/passed` 追加第二条语义相近事件。用户计划把"收敛 event 语义"放到最后，如果前面步骤新增更多事件类型，后面收敛的工作量会膨胀。— 缓解：在每个模块实现时就遵循统一事件命名，不等到最后集中清理。
- [RISK-5] **system_card_json 的前端编辑复杂度**：G0 gate 要求 system_card_json 非空，但它是一个自由结构 JSON 对象。GatePanel 中嵌入的编辑表单需要决定：是提供 JSON 文本框、还是结构化表单、还是先用 placeholder `{}`。— 缓解：最小方案先用 JSON 文本框 + 基本校验。

## 双视角对比

### 视角 A：llmdoc 既定路线

llmdoc 的建议顺序：
1. G1-G3 前半链（Figure Plan 生成/确认、资产上传与 AnalysisRun、Manifest/资产确认）
2. G4/G5 写作链

这条路线的逻辑：
- G0 后端已就绪，只缺前端入口，优先级可以低一些
- G1-G3 是"让数据流跑起来"的核心链路
- G4/G5 依赖 G1-G3 的数据，放后面

### 视角 B：用户新计划

用户的建议顺序：
1. 先补 G0 可操作性（前端编辑流）
2. 再补 G1/G4/G5 后端 API（用户已同意补入 G2/G3 缺口）
3. 再补前端真实工作台
4. 最后收敛 workflow 事件语义

这条路线的逻辑：
- G0 是第一个 gate，如果用户连 G0 都过不了，后面一切都无从谈起
- 从用户体验角度，G0 是入口

### 综合判断

**用户计划的合理之处：**
- G0 确实是用户流程第一步，不能操作 G0 就等于整个系统不可用。把它提前合理。
- G0 的实现成本极低（后端已就绪，前端约 3-5 文件），不会拖慢后续进度。
- 补完 G0 后可以立即验证端到端流程（创建 → 填写 → advance → 通过）。

**用户计划需要调整的地方：**
1. **"G1/G4/G5 后端 API" 应改为 "G1-G5 全链后端 API"**，因为 G2/G3 也有实质缺口（AnalysisRun API、资产确认/QC API）。
2. **G4/G5 后端 API 依赖 G1-G3 数据**（Draft 基于已批准 claims，Outline 基于 Evidence Matrix），建议后端 API 的实现顺序仍按 G1 → G2 → G3 → G4 → G5 推进，而不是跳步。
3. **"前端真实工作台"应该与后端 API 交错推进**，而不是全部后端做完再做前端。理由：G0 前端已经验证了"后端就绪 + 前端承接"模式，后续每个 gate 的前端可以紧跟后端落地，形成更快的验证闭环。
4. **"收敛 workflow event 语义"不应放到最后**。建议在每个模块实现时就遵循统一事件规范，而不是积累技术债到最后集中清理。

**建议的调整后顺序：**
1. G0 前端编辑流（最小成本，立即可用）
2. G1 后端 API + 前端承接（FigurePlan）
3. G2 后端 API 补齐 + 前端承接（AnalysisRun）
4. G3 后端 API 补齐 + 前端承接（资产确认/QC）
5. G4 后端 API + 前端承接（Evidence Matrix / Claims / Outline）
6. G5 后端 API + 前端承接（SectionDraft / Review / Approval）
7. 事件语义收敛（与步骤 2-6 同步进行，而非最后统一）

## 成功判据

- [OK-1] 用户在系统工作台页能编辑全部 G0 字段并保存（PATCH API 调用成功）。
- [OK-2] 保存后点击 Advance，G0 gate 通过（outcome = "accepted"，状态从 Draft → System_Defined）。
- [OK-3] GatePanel 在 G0 active 时展示 SystemDefinitionForm，blocker 高亮缺失字段。
- [OK-4] 后端新增的每个业务模块（evidence / drafts）遵循 repository → service → schemas → router 模板。
- [OK-5] 每个 gate 的后端 API 落地后，对应的 gate 校验能真正通过（不是假数据）。
- [OK-6] 生成类 API 统一返回 JobHandle，不同步返回产物。
- [OK-7] 前端工作台每个 gate 阶段有对应的操作入口（不要求完整编辑器，但至少有按钮/表单/状态展示）。
- [OK-8] 新增事件类型遵循 `reference/events-and-task-status.md` 既定规范。
- [OK-9] 不破坏现有测试基线和公共契约。

## 开放问题（已解决）

- Q1: 评估以哪种基线为准？ → A: 双视角并列 → 约束：综合判断章节
- Q2: G2/G3 如何处理？ → A: 补入缺口 → 约束：调整后顺序步骤 3-4
- Q3: G0 可操作性定义为什么？ → A: 系统页编辑流（GatePanel 嵌入 SystemDefinitionForm）→ 约束：[SC-2], [OK-1]-[OK-3]
