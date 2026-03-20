# Figure Plan Workbench Layout Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将图表规划工作台从重复的三栏结构收敛为“两栏 + 二级编辑层”，保留筛选、详情、编辑、删除和确认能力。

**Architecture:** 在 `FigurePlanWorkbench` 内合并左导航和中间卡片列表，保留页内局部状态管理；将原本详情区内联编辑迁移到新的覆盖层编辑面板，使右栏聚焦只读详情和后续动作。测试继续使用现有 Vitest + Testing Library 组件级回归测试。

**Tech Stack:** Next.js App Router、React、TypeScript、Vitest、Testing Library、inline CSSProperties

---

### Task 1: 更新组件测试以定义新交互

**Files:**
- Modify: `frontend/components/gates/g1/FigurePlanWorkbench.test.tsx`
- Reference: `frontend/components/gates/g1/FigurePlanWorkbench.tsx`

**Step 1: 写失败测试**

- 将筛选测试改为验证 `全部 / 未关联` 两个轻筛选入口
- 新增“点击编辑后打开覆盖层并保存”的断言

**Step 2: 运行单测确认失败**

Run: `npx vitest run components/gates/g1/FigurePlanWorkbench.test.tsx --config vitest.config.ts`

Expected: 至少 1 个断言失败，原因是旧布局仍然使用内联编辑或旧筛选结构。

### Task 2: 合并左导航与中间卡片列表

**Files:**
- Modify: `frontend/components/gates/g1/FigurePlanWorkbench.tsx`

**Step 1: 移除独立 figure_framework 导航列表**

- 删除左栏 `figure_framework` 筛选导航渲染
- 删除内联卡片编辑器和 `editingCardId`

**Step 2: 实现两栏布局**

- 左栏顶部添加轻筛选按钮
- 左栏主体改成统一卡片列表
- 点击卡片切换右栏详情

**Step 3: 运行单测**

Run: `npx vitest run components/gates/g1/FigurePlanWorkbench.test.tsx --config vitest.config.ts`

Expected: 筛选与选中行为通过，编辑相关测试仍失败。

### Task 3: 增加二级编辑层并接通现有 mutation

**Files:**
- Modify: `frontend/components/gates/g1/FigurePlanWorkbench.tsx`

**Step 1: 写最小编辑覆盖层**

- 新增 `editingPlanId`
- 用覆盖层承载现有编辑表单字段与保存/取消按钮

**Step 2: 复用现有 patch mutation**

- 保存时继续调用 `usePatchFigurePlan`
- 保存成功后关闭覆盖层

**Step 3: 从卡片和详情区都能打开编辑层**

- 卡片保留编辑按钮
- 详情区编辑按钮改为打开覆盖层

### Task 4: 验证删除与详情区行为未回归

**Files:**
- Modify: `frontend/components/gates/g1/FigurePlanWorkbench.tsx`
- Test: `frontend/components/gates/g1/FigurePlanWorkbench.test.tsx`

**Step 1: 确认删除后仍切换到下一个可见图表**

- 保持 `handleDeleteSuccess` 的选中回退逻辑

**Step 2: 保持右栏只读详情与既有动作**

- 保留确认规划、删除、素材上传、AI 讨论
- 去除右栏内联编辑状态分支

**Step 3: 运行组件测试**

Run: `npx vitest run components/gates/g1/FigurePlanWorkbench.test.tsx --config vitest.config.ts`

Expected: 全部通过。

### Task 5: 完整验证

**Files:**
- Modify: `frontend/components/gates/g1/FigurePlanWorkbench.tsx`
- Modify: `frontend/components/gates/g1/FigurePlanWorkbench.test.tsx`

**Step 1: 运行前端定向测试**

Run: `npx vitest run components/gates/g1/FigurePlanWorkbench.test.tsx --config vitest.config.ts`

Expected: PASS

**Step 2: 运行静态检查**

Run: `npm run typecheck`

Expected: 若失败，明确标注是否为仓库中已有无关问题。
