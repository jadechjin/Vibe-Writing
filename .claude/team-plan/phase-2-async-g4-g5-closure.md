# Team Plan: phase-2-async-g4-g5-closure

## 概述
基于当前已落地的 G0-G3 与 thin workflow/task event 底座，下一阶段优先把 Figure Plan / Evidence Matrix / Outline / Section Draft 补成真实异步持久化链路，再接通 G4/G5 前端工作台，最后做集成验收与回归。

## Codex 分析摘要
- 当前方案技术上可行，不需要重构工作流底座；最稳妥路径是复制 `Manifest` 已有的“start workflow → 返回 handle → 后台任务落库 → 追加 task event”模式到 Figure Plan、Evidence Matrix、Outline、Section Draft。
- 后端 gate 规则本身已经具备，当前真正缺口是：生成端点没有完整异步落库闭环、缺少支撑 G4/G5 面板回显的只读接口、前端尚未接通实际操作流。
- `system_sections` 是当前唯一必须前置确认的高风险点：`SystemSection` 模型与读取路径已存在，`SystemDetail` 也会回传 `sections`，但 `create_system` 目前没有明确物化 section 的写入逻辑；如果不先补齐，G4 claim 审批与 G5 section draft 会被结构性卡住。
- 后端并行拆分建议是：`evidence` 模块与 `drafts` 模块分别作为独立 worker，`systems` 的 section 预检/补齐放在最前，事件语义与统一验证放到最后一层。

## Gemini 分析摘要
- G4 最合适的交互是“Evidence Matrix + Outline”单面板闭环：先触发生成，再在同一面板内查看 claims、审批 claim、绑定 evidence、查看 outline 与 outline-asset binding，不重做 MainShell / Workbench 壳层。
- G5 最合适的交互是按 section 的逐节草稿工作流：左侧 section 列表，右侧展示该节草稿、可用 claims、review comments 与 approve 操作。
- 前端应保持现有 `GatePanel + React Query + StatusTray` 模式，不把 G4/G5 状态塞回 `useProjectStatus`；`useProjectStatus` 继续只负责 workflow snapshot / gate 派生。
- 为避免多人并行冲突，应把共享壳层修改单独收敛到 `GatePanel.tsx` 与系统页；G4 与 G5 分别拥有独立 hooks 与独立 panel 文件。

## 技术方案

### 1. 总体策略
1. 继续沿用 thin workflow + task event，不扩 Temporal 长流程。
2. 所有生成类动作统一返回 handle，不同步返回最终工件。
3. 后端以 `Manifest` 现有异步实现为唯一模板复制到：
   - Figure Plan
   - Evidence Matrix
   - Outline
   - Section Draft
4. 前端保持：
   - 系统页只负责注入 `GatePanel` / `StatusTray`
   - `GatePanel` 只做 gate-to-panel 路由与共享 props 下传
   - G4/G5 的真实数据通过各自 hooks 读取，不扩 `useProjectStatus`

### 2. Builder 无决策规则
1. **section 来源规则固定**：
   - 优先读取 `project.thesis_schema_json.outline`
   - 若不存在，则读取 `project.thesis_schema_json.chapters`
   - 仍为空时，回退到文档默认 4 段骨架：引言、实验材料与方法、结果与讨论、本章小结
2. **事件模式固定**：生成端点统一按 `Manifest` 模式处理，先返回 `202 + handle`，后台任务成功后写入 `TASK_SUCCEEDED`，失败则写 `TASK_FAILED`。
3. **前端状态边界固定**：
   - `useProjectStatus` 不承担 claims / drafts 资源缓存
   - G4 数据全部进入 `useEvidence.ts`
   - G5 数据全部进入 `useDrafts.ts`
4. **共享壳层单点修改**：只有 Task 3 可以改 `GatePanel.tsx` 与系统页；Task 4/5 禁止再碰这两个文件。

### 3. 关键决策
- Evidence Matrix 继续以 `claims + claim_evidence_links` 组合表达，不新增独立 truth-layer 表。
- Outline 与 Section Draft 保持现有表模型，补足版本号生成、后台创建与回显查询。
- 首轮只做最小可用 UI：列表、状态、触发按钮、必要表单、错误提示、阻塞提示；不做拖拽编排或富文本编辑器升级。
- `StatusTray` 继续作为异步任务感知主通道；系统页只补必要的失效刷新规则。

## 子任务列表

### Task 0: 补齐 system sections 来源
- **类型**: 后端
- **文件范围**:
  - `backend/app/modules/systems/service.py`
  - `backend/app/modules/systems/repository.py`
  - `backend/tests/modules/systems/test_systems_api.py`
- **依赖**: 无
- **实施步骤**:
  1. 在 `create_system` 流程中读取所属 project 的 `thesis_schema_json`，按“outline → chapters → 默认 4 段骨架”的顺序解析 section 源。
  2. 在 systems repository 中新增最小 section 物化 helper，创建 `SystemSection` 记录并保证 `order_no`、`section_key` 唯一性。
  3. 保持 `get_system_detail` 返回的 `sections` 契约不变，只让其从空列表变为真实 section 列表。
  4. 为系统创建与详情读取补测试，断言新建 system 后 `sections` 非空且顺序稳定。
- **验收标准**:
  - 新创建的 system 可以稳定返回 `sections`。
  - 没有 thesis schema 时也能落默认 section 骨架。
  - 不修改 project API 契约。

### Task 1: 完成 evidence 异步生成闭环
- **类型**: 后端
- **文件范围**:
  - `backend/app/modules/evidence/service.py`
  - `backend/app/modules/evidence/router.py`
  - `backend/app/modules/evidence/repository.py`
  - `backend/tests/modules/evidence/test_evidence_api.py`
- **依赖**: Task 0
- **实施步骤**:
  1. 在 evidence repository 中补齐 Figure Plan 版本 helper、system sections 查询、claim evidence-links 查询 helper。
  2. 在 evidence service 中新增 `run_* / complete_* / failure_*` 三段式后台任务，分别承接 Figure Plan 与 Evidence Matrix。
  3. 把 `POST /systems/{id}/figure-plans/generate` 与 `POST /systems/{id}/evidence-matrix/generate` 改为返回 `202 + handle` 后立即启动后台任务。
  4. 后台任务成功时创建 FigurePlan / Claim / ClaimEvidenceLink 真实记录，并追加 workflow/task success 事件；失败时追加 failed 事件并保留错误信息。
  5. 保持现有 claim approve 与 evidence bind 约束不变，只补生成和回显闭环。
- **验收标准**:
  - 两个 generate 端点都返回 handle，不同步返回最终工件。
  - 后台任务结束后，Figure Plan/Claim 数据真实可查。
  - claim approve 的 section 校验与 evidence 绑定约束仍通过现有测试。

### Task 2: 完成 drafts 异步生成闭环
- **类型**: 后端
- **文件范围**:
  - `backend/app/modules/drafts/service.py`
  - `backend/app/modules/drafts/router.py`
  - `backend/app/modules/drafts/repository.py`
  - `backend/tests/modules/drafts/test_drafts_api.py`
- **依赖**: Task 0
- **实施步骤**:
  1. 在 drafts repository 中补齐 outline / section draft 版本 helper，并保留现有 `list_outline_bindings`、`list_review_comments` 读接口能力。
  2. 在 drafts service 中新增 `run_* / complete_* / failure_*` 异步任务，分别承接 Outline 与 Section Draft。
  3. 把 `POST /systems/{id}/outline/generate` 与 `POST /systems/{id}/sections/{sectionKey}/draft` 改为返回 `202 + handle` 后后台落库。
  4. 为 outline bindings 与 review comments 补最小只读接口，保证前端刷新后能还原真实状态。
  5. 复用现有“仅允许当前 system 的 approved claims 生成 section draft”的校验，不重写业务规则。
- **验收标准**:
  - Outline/Section Draft 都能通过后台任务真实落库。
  - G5 所需的 draft、review comments、outline bindings 可以查询回显。
  - 既有 drafts API 测试继续通过，并新增异步闭环测试。

### Task 3: 收敛前端共享壳层与失效刷新
- **类型**: 前端
- **文件范围**:
  - `frontend/components/gates/GatePanel.tsx`
  - `frontend/app/projects/[projectId]/systems/[systemId]/page.tsx`
- **依赖**: Task 0
- **实施步骤**:
  1. 让系统页明确向 `GatePanel` 传入 `systemId` 与 `systemDetail` 的 section 信息来源。
  2. 在 `GatePanel` 中把 `systemDetail.sections` 下传给 G4/G5 面板，避免 G4/G5 自行改壳层拉共享数据。
  3. 在系统页的 `handleInvalidate` 中补充对关键 task 完成/失败事件的 workflow 失效刷新，缩短 G4/G5 生成完成后的等待感知。
  4. 调整 G4/G5 面板标题/描述文案，使其与实际生成-确认-审批路径一致。
- **验收标准**:
  - `GatePanel` 成为 G4/G5 的唯一共享 props 入口。
  - Task 4/5 不需要再改系统页与 `GatePanel.tsx`。
  - 生成任务完成后，工作台能及时刷新到新状态。

### Task 4: 接通 G4 前端工作台
- **类型**: 前端
- **文件范围**:
  - `frontend/hooks/useEvidence.ts`
  - `frontend/components/gates/EvidenceMatrixPanel.tsx`
- **依赖**: Task 1, Task 3
- **实施步骤**:
  1. 新增 `useEvidence.ts`，收敛 Figure Plan、Claims、Evidence Links、Outline、Outline Bindings 相关 query/mutation。
  2. 将 `EvidenceMatrixPanel` 从 TODO 面板改为真实工作台：支持生成 Evidence Matrix、查看 claims、approve claim、绑定 evidence、生成 outline、确认 outline、查看 outline 绑定结果。
  3. 保留 blocker 展示，并在按钮禁用态上明确提示前置条件不足原因。
  4. mutation 成功后只失效自身 query key 与 `['workflow', systemId]`，不改 `useProjectStatus` 结构。
- **验收标准**:
  - G4 面板不再有禁用占位按钮。
  - claim 审批与 evidence 绑定可以在前端真实完成。
  - outline 生成/确认状态能在同一面板回显。

### Task 5: 接通 G5 前端工作台
- **类型**: 前端
- **文件范围**:
  - `frontend/hooks/useDrafts.ts`
  - `frontend/components/gates/DraftPanel.tsx`
- **依赖**: Task 2, Task 3
- **实施步骤**:
  1. 新增 `useDrafts.ts`，收敛 section drafts、review comments、approve draft 等 query/mutation。
  2. 将 `DraftPanel` 从 TODO 面板改为按 section 的工作台：支持选择 section、查看可用 claims、触发 section draft 生成、查看最新草稿、提交 review comment、approve draft。
  3. 基于 `systemDetail.sections` 渲染 section 列表与状态，保证 section 顺序与后端一致。
  4. 对“无 approved claims / 未完成 outline”等场景显示明确阻塞提示，而不是静默失败。
- **验收标准**:
  - G5 面板可以逐节生成与审批草稿。
  - review comments 可以真实提交并回显。
  - 草稿状态变化后，工作台与 StatusTray 展示一致。

### Task 6: 做集成验收与回归补强
- **类型**: 测试 / 集成
- **文件范围**:
  - `backend/tests/integration/test_phase2_async_g4_g5_flow.py`
  - `frontend/e2e/g4-g5-workbench.spec.ts`
- **依赖**: Task 1, Task 2, Task 4, Task 5
- **实施步骤**:
  1. 新增后端集成测试，覆盖“create system → sections 就绪 → generate evidence matrix → generate outline → generate section draft”主链。
  2. 新增前端 E2E，覆盖 G4 claim 审批/绑定、G5 draft 生成/review/approve 的关键用户路径。
  3. 若回归暴露事件延迟或状态漂移，只在测试层面定位与记录，不回头扩大改动范围到任务服务重构。
- **验收标准**:
  - 后端集成测试能证明异步主链闭环。
  - 前端 E2E 能证明 G4/G5 面板对真实 API 可操作。
  - 本轮不引入新的跨模块共享状态黑盒。

## 文件冲突检查
⚠️ 已通过依赖关系解决

- `backend/app/modules/systems/*` 仅由 Task 0 修改，后续任务只消费其结果。
- `backend/app/modules/evidence/*` 与 `backend/app/modules/drafts/*` 完全隔离，可并行。
- `frontend/components/gates/GatePanel.tsx` 与系统页只由 Task 3 修改；Task 4/5 禁止再次编辑这两个文件。
- `frontend/hooks/useEvidence.ts` 与 `frontend/hooks/useDrafts.ts` 分别归 Task 4/5 所有，互不重叠。
- 集成与 E2E 测试集中在 Task 6 新文件中，不回写前面任务的实现文件。

## 并行分组
- **Layer 0（串行前置）**: Task 0
- **Layer 1（并行）**: Task 1, Task 2, Task 3
- **Layer 2（并行）**: Task 4, Task 5
- **Layer 3（串行收口）**: Task 6

## 推荐 Builder 配置
- 最少 5 个 Builder：1 个前置/收口 + 2 个后端 + 2 个前端
- 理想 6 个 Builder：Task 0/6 独立 1 个，Task 1/2/3/4/5 各 1 个

## 执行备注
- 本计划的主优先级是把“异步生成真实落库”与“G4/G5 前端真实可操作”做成闭环；`current_gate` 语义清理、重复事件收敛、llmdoc 同步不在本轮核心实施范围内。
- 如果实施前想降低上下文负担，建议在批准后先 `/clear`，再运行 `/ccg:team-exec`。