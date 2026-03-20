from enum import StrEnum


class GateKey(StrEnum):
    G0 = "G0"
    G1 = "G1"
    G2 = "G2"
    G3 = "G3"


class GateRequirementKey(StrEnum):
    SYSTEM_DEFINED = "System_Defined"
    FIGURE_PLAN_READY = "Figure_Plan_Ready"
    DATA_UPLOADED = "Data_Uploaded"
    ANALYSIS_READY = "Analysis_Ready"
    ASSETS_CONFIRMED = "Assets_Confirmed"
    EVIDENCE_MATRIX_READY = "Evidence_Matrix_Ready"
    OUTLINE_READY = "Outline_Ready"
    CHAPTER_APPROVED = "Chapter_Approved"


class SystemState(StrEnum):
    DRAFT = "Draft"
    SYSTEM_DEFINED = "System_Defined"
    FIGURE_PLAN_READY = "Figure_Plan_Ready"
    DATA_PENDING = "Data_Pending"
    DATA_UPLOADED = "Data_Uploaded"
    ANALYSIS_READY = "Analysis_Ready"
    ASSETS_CONFIRMED = "Assets_Confirmed"
    EVIDENCE_MATRIX_READY = "Evidence_Matrix_Ready"
    OUTLINE_READY = "Outline_Ready"
    SECTION_DRAFTING = "Section_Drafting"
    CHAPTER_REVIEW = "Chapter_Review"
    CHAPTER_APPROVED = "Chapter_Approved"


class TaskStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_USER = "waiting_user"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EventType(StrEnum):
    TASK_CREATED = "task.created"
    TASK_STARTED = "task.started"
    TASK_PROGRESS = "task.progress"
    TASK_WAITING_USER = "task.waiting_user"
    TASK_SUCCEEDED = "task.succeeded"
    TASK_FAILED = "task.failed"
    WORKFLOW_STATE_CHANGED = "workflow.state_changed"
    GATE_BLOCKED = "gate.blocked"
    GATE_PASSED = "gate.passed"


class ExecutorKind(StrEnum):
    CLAUDE_CODE = "claude_code"
    VISION = "vision"
    PYTHON_ANALYSIS = "python_analysis"


class ReviewDecision(StrEnum):
    APPROVE = "approve"
    REQUEST_CHANGES = "request_changes"
    FREEZE = "freeze"


def coerce_gate_key(raw: str | None) -> GateKey | None:
    """Normalize legacy gate keys (G4/G5) to new 4-gate scheme.

    Current valid keys (G0-G3) pass through unchanged.
    Only truly legacy keys from the old 6-gate scheme are remapped:
      old G2 (Figure Plan) -> new G1
      old G3 (Assets)      -> new G2
      old G4 (Evidence)    -> new G2
      old G5 (Drafting)    -> new G3
    """
    if raw is None:
        return None
    # Current keys pass through first
    try:
        return GateKey(raw)
    except ValueError:
        pass
    # Legacy-only remapping (old keys that no longer exist in GateKey)
    _LEGACY_GATE_MAP: dict[str, GateKey] = {
        "G4": GateKey.G2,
        "G5": GateKey.G3,
    }
    return _LEGACY_GATE_MAP.get(raw)


GATE_REQUIREMENTS: dict[GateKey, tuple[GateRequirementKey, ...]] = {
    GateKey.G0: (GateRequirementKey.SYSTEM_DEFINED,),
    GateKey.G1: (GateRequirementKey.FIGURE_PLAN_READY, GateRequirementKey.DATA_UPLOADED, GateRequirementKey.ANALYSIS_READY),
    GateKey.G2: (GateRequirementKey.ASSETS_CONFIRMED, GateRequirementKey.EVIDENCE_MATRIX_READY, GateRequirementKey.OUTLINE_READY),
    GateKey.G3: (GateRequirementKey.CHAPTER_APPROVED,),
}
