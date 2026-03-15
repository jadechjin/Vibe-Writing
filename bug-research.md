# bug.md 代码实现研究报告

## 研究日期：2026-03-14

---

## 一、当前代码现状

### G0 骨架生成

- Prompt 位置：`backend/app/modules/skeletons/service.py:419-514`
- `skeleton_json` 已包含 `figure_framework` 数组，每项有：
  - `figure_id`, `title`, `type`, `data_source`, `purpose`
  - `related_sections[]`, `addresses_questions[]`
- 骨架确认时（`confirm_skeleton` L270-319）会同步 `SystemSection`
- 骨架模型：`backend/app/persistence/models/skeleton.py` — `StructureSkeleton`

### G1 Figure Plan

- 模型：`backend/app/persistence/models/evidence.py:11-42` — `FigurePlan`
  - 字段：`system_id`, `figure_no`, `title`, `claim_text`, `data_needed_json`, `method_json`, `acceptance_criteria_json`, `status`, `version`
  - **无** `section_key` 或骨架关联字段
- 生成逻辑：`backend/app/modules/evidence/service.py:150-185`
  - 硬编码 stub，只创建一个 placeholder plan
  - **不读取骨架的 figure_framework**
- 前端面板：`frontend/components/gates/FigurePlanPanel.tsx` — 简单列表展示
- 前端 hook：`frontend/hooks/useFigurePlan.ts`

### 核心问题确认

bug.md 指出的问题在代码中完全成立：

1. `figure_framework` 在 G0 生成但 G1 完全不消费
2. `FigurePlan` 没有 `section_key`，图片与文章结构脱节
3. G1 前端是扁平列表，不是骨架驱动的工作台

---

## 二、改动一：G0 增强（小改动）

### 目标

在 skeleton prompt 的 `figure_framework` 中增加 bug.md 要求的字段。

### 改动清单

| 文件 | 改动 |
|------|------|
| `backend/app/modules/skeletons/service.py` L459-468 | `figure_framework` schema 增加 `importance: "high\|medium\|low"` 和 `data_preparation: "用户需要准备什么数据"` |
| `backend/app/modules/skeletons/service.py` L516+ | `SKELETON_REVISE_PROMPT` 同步增加字段 |
| `frontend/components/gates/g0/SkeletonOverlay.tsx` | 骨架详情中渲染 figure_framework 的建议信息 |

### 不涉及

- 数据库 migration（skeleton_json 是 JSON 字段，schema 变化不影响存储）
- 后端 API 契约变化

---

## 三、改动二：G1 重构（大改动）

### 3.1 后端：FigurePlan 模型扩展

**文件**：`backend/app/persistence/models/evidence.py`

新增字段：

```python
section_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
skeleton_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
brief_text: Mapped[str | None] = mapped_column(Text, nullable=True)
brief_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

**需要新 Alembic migration**（006_figure_plan_skeleton_binding.py）

### 3.2 后端：Figure Plan 生成重写

**文件**：`backend/app/modules/evidence/service.py:150+`

当前 `complete_figure_plan_generation` 是 stub。重写逻辑：

```python
async def complete_figure_plan_generation(session, *, workflow_id, system_id, broadcaster):
    # 1. 获取最新 confirmed skeleton
    skeleton = session.scalars(
        select(StructureSkeleton)
        .where(system_id=system_id, status="confirmed")
        .order_by(StructureSkeleton.version.desc())
        .limit(1)
    ).first()

    # 2. 读取 figure_framework
    figures = (skeleton.skeleton_json or {}).get("figure_framework", [])

    # 3. 为每个 figure suggestion 创建 FigurePlan
    for fig in figures:
        plan = FigurePlan(
            system_id=system_id,
            figure_no=fig["figure_id"],
            title=fig["title"],
            claim_text=fig.get("purpose", ""),
            section_key=fig.get("related_sections", [None])[0],
            skeleton_version=skeleton.version,
            status="pending",
            ...
        )
```

### 3.3 后端：骨架变更联动

**文件**：`backend/app/modules/skeletons/service.py:270-319`

在 `confirm_skeleton` 中增加 FigurePlan 影响检测：

```python
# 现有：检测受影响的 claims
affected_claims = [...]

# 新增：检测受影响的 figure plans
figure_plans = session.scalars(
    select(FigurePlan).where(
        FigurePlan.system_id == system_id,
        FigurePlan.section_key.isnot(None),
    )
).all()

for plan in figure_plans:
    if plan.section_key not in new_section_keys:
        plan.status = "needs_review"  # 待复核
    elif plan.skeleton_version != skeleton.version:
        plan.status = "needs_review"  # 骨架版本变更
```

### 3.4 后端：状态机扩展

bug.md 建议的状态流：

```
pending → uploaded → analyzing → discussing → draft_brief → confirmed → delivered
特殊状态：needs_review（因骨架变更待复核）
```

需要在 `backend/app/common/enums.py` 或 evidence service 中定义。

### 3.5 前端：G1 三栏工作台

**重构文件**：`frontend/components/gates/FigurePlanPanel.tsx`

布局：

```
┌──────────────┬──────────────────┬──────────────────┐
│  左栏：骨架树  │  中栏：图任务列表  │  右栏：图任务详情  │
│              │                  │                  │
│ - 章节列表    │ - G0 推荐图位     │ - 上下文信息      │
│ - 可编辑      │ - 用户新增图位     │ - 素材上传区      │
│ - 单一事实源   │ - 已上传任务      │ - 对话区          │
│              │ - 待补图位        │ - Brief 定稿区    │
│              │                  │ - 历史记录        │
└──────────────┴──────────────────┴──────────────────┘
```

**新增 hooks**：

- `useFigurePlansBySection(systemId, sectionKey)` — 按节点过滤
- 或修改现有 `useFigurePlans` 返回按 section 分组的数据

**类型变更**：`frontend/hooks/useFigurePlan.ts`

```typescript
export type FigurePlanDetail = {
  // 现有字段...
  sectionKey: string | null      // 新增
  skeletonVersion: number | null // 新增
  briefText: string | null       // 新增
  briefConfirmedAt: string | null // 新增
}
```

**GatePanel 配置**：`frontend/components/gates/GatePanel.tsx:71-77`

```typescript
case "G1":
  return {
    title: "图证工作台",  // 改名
    description: "基于文章骨架规划图表证据。每个章节的图片必须服务文章结构和论证。",
    actionLabel: "推进门禁",
    actionHint: "所有图表规划确认后可推进至数据上传阶段。",
  }
```

---

## 四、实施顺序（依赖链）

```
Phase 1: G0 prompt 增强（独立，无依赖）
    ↓
Phase 2: FigurePlan 模型扩展 + Alembic migration
    ↓
Phase 3: figure_plan_generation 重写（依赖 Phase 2）
    ↓
Phase 4: confirm_skeleton 联动 FigurePlan（依赖 Phase 2）
    ↓
Phase 5: 前端 G1 三栏工作台（依赖 Phase 2-4 的 API 契约）
```

Phase 1 可以独立先做。Phase 2-5 是一个完整的 G1 重构。

---

## 五、风险与约束

| 风险 | 影响 | 缓解 |
|------|------|------|
| FigurePlan migration 与现有数据兼容 | 新字段需 nullable | 所有新字段设为 nullable |
| 骨架变更联动复杂度 | 节点删除/拆分/合并 | 先只处理"节点内容修改"和"节点删除"两种情况 |
| G1 三栏 UI 工作量大 | 全新组件 | 可分步：先做左+中两栏，右栏后续迭代 |
| figure_framework 格式不稳定 | AI 输出可能缺字段 | 解析时做 defensive coding，缺失字段给默认值 |

---

## 六、与现有 task 的关系

当前 `.trellis/tasks/03-13-remove-system-definition-fields/` 是清理 system definition 字段的任务，与本次 G0/G1 改动无关。建议完成该 task 后，再创建新 task 处理 bug.md 的内容。
