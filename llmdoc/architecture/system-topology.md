# 系统拓扑

## 总体结构

```text
[Next.js Frontend Workbench]
          |
          v
[FastAPI API + Domain Services + Temporal Workflow]
          |
          +-----------------------+
          |                       |
          v                       v
[PostgreSQL / Redis / MinIO]   [Claude Code / Vision / Python Workers]
```

## 分层职责

### 前端

负责：项目总览、实验体系、资产、Evidence、Drafting、Gates、任务托盘。

### 后端

负责：状态管理、门禁校验、任务编排、审批、版本追踪、文件元数据、统一 API。

### 工作流层

当前仓库以 thin workflow / task event 模式承接主链路：`system_workflow.py` 仍是薄适配层，负责最小异步触发与状态回写。Phase 2 继续沿用 thin workflow + task event 模式，不扩展 Temporal 为真实长流程编排。G0-G5 全链闭环完成后再评估是否需要更完整的 workflow 能力。

### 执行层

Claude Code、Vision、Python worker 只负责受控执行，不掌握系统真相。
