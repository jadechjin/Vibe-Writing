# 论文工作流系统 llmdoc

## 阅读顺序

1. `overview/product.md`
2. `overview/repository-status.md`
3. `overview/workflow-summary.md`
4. `architecture/system-topology.md`
5. `architecture/backend-modules.md`
6. `architecture/frontend-workbench.md`
7. `architecture/workflow-and-gates.md`
8. `reference/api-contracts.md`
9. `reference/events-and-task-status.md`
10. `reference/data-models.md`
11. `guides/builder-execution-order.md`
12. `guides/local-development.md`

## 项目定义

这是一个以实验体系为最小业务单元、以 Evidence Matrix 为唯一事实源、以 G0–G5 门禁推进、以 FastAPI + Temporal + Next.js 为基础设施的论文工作流平台。

## 当前阶段

当前仓库已完成 Phase 1.5（控制平面收口 / 系统主链打通），前端工作台装配已闭环。Phase 2 方向：先补 G0 可操作性（GET /systems/{id} 端点 + SystemDefinitionForm 编辑流），然后按 G1→G2→G3→G4→G5 逐 gate 全链闭环，包括 evidence/drafts 模块从空包起建、各 gate 工作台面板承接。详见 `.claude/team-plan/g0-g5-full-chain.md`。

## 核心不变式

- Claude Code 是受控执行器，不是系统主体。
- 所有生成类动作统一异步执行并返回句柄。
- Draft 只能基于已批准 claims。
- 非法 `claim.section_ref` 不得在 G4/G5 之前进入 approved truth layer（已批准 Evidence Matrix 真相层）；claim 审批先校验其是否属于当前 system 的 `system_sections.section_key` 集合，G4 再做兜底阻断，G5 保留最终防线。
- Manifest 是独立持久化实体。
- Evidence 面板固定为双栏主视图。
- WebSocket 是长任务反馈主通道。
