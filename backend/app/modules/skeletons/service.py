from __future__ import annotations

import asyncio
import json
import logging
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from inspect import isawaitable
from pathlib import Path
from typing import Any, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.common.enums import EventType, GateKey, TaskStatus
from app.common.errors import ErrorCode
from app.common.events import TaskEvent
from app.common.schemas import JobHandle
from app.common.storage import download_asset_to_temp
from app.core.exceptions import AppException
from app.modules.skeletons import repository
from app.modules.skeletons.schemas import (
    SkeletonConfirmResponse,
    SkeletonDetail,
    SkeletonGenerateRequest,
    SkeletonPatchRequest,
    SkeletonReviseRequest,
    SkeletonSummary,
)
from app.modules.tasks.service import TaskWorkflowService
from app.persistence.models.asset import Asset
from app.persistence.models.evidence import Claim
from app.persistence.models.skeleton import StructureSkeleton
from app.persistence.models.system import ExperimentalSystem, SystemSection
from app.realtime.broadcaster import TaskBroadcaster
from app.workflows.system_workflow import (
    WorkflowCommand,
    WorkflowEventCommand,
    append_system_workflow_event,
    start_system_workflow,
)

logger = logging.getLogger(__name__)

SKELETON_TASK_START_DELAY_SECONDS = 0.05
CLAUDE_CLI_TIMEOUT_SECONDS = 300

SessionLike = AsyncSession | Session
T = TypeVar("T")


class _SyncTaskSessionAdapter:
    def __init__(self, session: Session) -> None:
        self.sync_session = session

    def add(self, instance: object) -> None:
        self.sync_session.add(instance)

    async def flush(self) -> None:
        self.sync_session.flush()

    async def refresh(self, instance: object) -> None:
        self.sync_session.refresh(instance)

    async def execute(self, statement):
        return self.sync_session.execute(statement)

    async def commit(self) -> None:
        self.sync_session.commit()

    async def rollback(self) -> None:
        self.sync_session.rollback()


async def _maybe_await(value: T) -> T:
    if isawaitable(value):
        return await value
    return value


def _to_detail(s: StructureSkeleton) -> SkeletonDetail:
    return SkeletonDetail(
        id=s.id,
        system_id=s.system_id,
        version=s.version,
        skeleton_json=s.skeleton_json or {},
        change_summary=s.change_summary,
        source_asset_ids=s.source_asset_ids or [],
        status=s.status,
        confirmed_at=s.confirmed_at,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


def _to_summary(s: StructureSkeleton) -> SkeletonSummary:
    return SkeletonSummary(
        id=s.id,
        version=s.version,
        status=s.status,
        change_summary=s.change_summary,
        created_at=s.created_at,
    )


async def _load_system(session: SessionLike, system_id: str) -> ExperimentalSystem:
    system = await repository.get_system(session, system_id)
    if system is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="System not found",
            status_code=404,
            details={"system_id": system_id},
        )
    return system


async def _load_skeleton(session: SessionLike, skeleton_id: str) -> StructureSkeleton:
    skeleton = await repository.get_skeleton_by_id(session, skeleton_id)
    if skeleton is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="Skeleton not found",
            status_code=404,
            details={"skeleton_id": skeleton_id},
        )
    return skeleton


def _get_task_session(session: SessionLike) -> AsyncSession | _SyncTaskSessionAdapter:
    if isinstance(session, AsyncSession):
        return session
    if isinstance(session, Session):
        return _SyncTaskSessionAdapter(session)
    return _SyncTaskSessionAdapter(session.sync_session)  # type: ignore[arg-type]


async def generate_skeleton(
    session: SessionLike,
    system_id: str,
    payload: SkeletonGenerateRequest,
    broadcaster: TaskBroadcaster | None = None,
) -> JobHandle:
    system = await _load_system(session, system_id)
    task_service = TaskWorkflowService(_get_task_session(session))  # type: ignore[arg-type]
    started = await start_system_workflow(
        task_service,
        WorkflowCommand(
            project_id=system.project_id,
            system_id=system.id,
            workflow_key="skeleton_generate",
            current_state=system.status,
            target_state=system.status,
            current_gate=GateKey.G0.value,
            status=TaskStatus.QUEUED,
            context={
                "source_asset_ids": payload.source_asset_ids,
                "user_intent": payload.user_intent,
            },
            message="Skeleton generation started",
            event_type=EventType.TASK_CREATED,
        ),
    )
    await _maybe_await(session.commit())

    if broadcaster is not None:
        await _publish_task_event(
            broadcaster,
            type=EventType.TASK_CREATED,
            task_id=started.handle.job_id,
            workflow_id=started.handle.workflow_id,
            project_id=system.project_id,
            system_id=system.id,
            status=TaskStatus.QUEUED,
            message="Skeleton generation started",
        )

    return started.handle


async def list_skeletons(session: SessionLike, system_id: str) -> list[SkeletonSummary]:
    await _load_system(session, system_id)
    skeletons = await repository.list_skeletons(session, system_id)
    return [_to_summary(s) for s in skeletons]


async def get_skeleton(session: SessionLike, skeleton_id: str) -> SkeletonDetail:
    skeleton = await _load_skeleton(session, skeleton_id)
    return _to_detail(skeleton)


async def patch_skeleton(
    session: SessionLike,
    skeleton_id: str,
    payload: SkeletonPatchRequest,
) -> SkeletonDetail:
    skeleton = await _load_skeleton(session, skeleton_id)

    if skeleton.status == "confirmed":
        next_version = await repository.get_next_version(session, skeleton.system_id)
        new_skeleton = StructureSkeleton(
            system_id=skeleton.system_id,
            version=next_version,
            skeleton_json=payload.skeleton_json or skeleton.skeleton_json,
            change_summary=payload.change_summary or skeleton.change_summary,
            source_asset_ids=skeleton.source_asset_ids,
            status="draft",
        )
        session.add(new_skeleton)
        await _maybe_await(session.flush())
        await _maybe_await(session.commit())
        return _to_detail(new_skeleton)

    if payload.skeleton_json is not None:
        skeleton.skeleton_json = payload.skeleton_json
    if payload.change_summary is not None:
        skeleton.change_summary = payload.change_summary
    skeleton.updated_at = datetime.now(UTC)
    await _maybe_await(session.flush())
    await _maybe_await(session.commit())
    return _to_detail(skeleton)


async def confirm_skeleton(
    session: SessionLike,
    skeleton_id: str,
) -> SkeletonConfirmResponse:
    skeleton = await _load_skeleton(session, skeleton_id)

    if skeleton.status == "confirmed":
        return SkeletonConfirmResponse(skeleton=_to_detail(skeleton), affected_claims=[])

    skeleton.status = "confirmed"
    skeleton.confirmed_at = datetime.now(UTC)
    skeleton.updated_at = datetime.now(UTC)

    sections_data = (skeleton.skeleton_json or {}).get("sections", [])
    system_id = skeleton.system_id

    result = await _maybe_await(session.execute(
        select(SystemSection).where(SystemSection.system_id == system_id)
    ))
    existing_sections = list(result.scalars().all())
    for sec in existing_sections:
        await _maybe_await(session.delete(sec))
    await _maybe_await(session.flush())

    for idx, sec in enumerate(sections_data):
        new_section = SystemSection(
            system_id=system_id,
            section_key=sec.get("key", f"section_{idx}"),
            title=sec.get("title", ""),
            order_no=idx,
        )
        session.add(new_section)
    await _maybe_await(session.flush())

    new_section_keys = {sec.get("key", f"section_{idx}") for idx, sec in enumerate(sections_data)}
    claim_result = await _maybe_await(session.execute(
        select(Claim).where(
            Claim.system_id == system_id,
            Claim.status == "approved",
        )
    ))
    all_approved_claims = list(claim_result.scalars().all())
    affected = [
        {"claim_id": c.claim_id, "section_ref": c.section_ref}
        for c in all_approved_claims
        if c.section_ref not in new_section_keys
    ]

    await _maybe_await(session.commit())
    return SkeletonConfirmResponse(skeleton=_to_detail(skeleton), affected_claims=affected)
async def revise_skeleton(
    session: SessionLike,
    system_id: str,
    payload: SkeletonReviseRequest,
    broadcaster: TaskBroadcaster | None = None,
) -> JobHandle:
    system = await _load_system(session, system_id)
    skeleton = await _load_skeleton(session, payload.skeleton_id)
    task_service = TaskWorkflowService(_get_task_session(session))  # type: ignore[arg-type]
    started = await start_system_workflow(
        task_service,
        WorkflowCommand(
            project_id=system.project_id,
            system_id=system.id,
            workflow_key="skeleton_revise",
            current_state=system.status,
            target_state=system.status,
            current_gate=GateKey.G0.value,
            status=TaskStatus.QUEUED,
            context={
                "skeleton_id": skeleton.id,
                "feedback": payload.feedback,
            },
            message="Skeleton revision started",
            event_type=EventType.TASK_CREATED,
        ),
    )
    await _maybe_await(session.commit())

    if broadcaster is not None:
        await _publish_task_event(
            broadcaster,
            type=EventType.TASK_CREATED,
            task_id=started.handle.job_id,
            workflow_id=started.handle.workflow_id,
            project_id=system.project_id,
            system_id=system.id,
            status=TaskStatus.QUEUED,
            message="Skeleton revision started",
        )

    return started.handle


# ---------------------------------------------------------------------------
# Background task helpers
# ---------------------------------------------------------------------------

def get_skeleton_task_session_bind(session: SessionLike) -> tuple[object, bool]:
    if isinstance(session, AsyncSession):
        bind = session.bind
        if bind is None:
            raise RuntimeError("Async session is not bound")
        return bind, True
    if isinstance(session, Session):
        return session.get_bind(), False
    return session.sync_session.get_bind(), False  # type: ignore[attr-defined]


async def _download_assets_to_dir(
    session: SessionLike,
    asset_ids: list[str],
    system_id: str,
    dest_dir: Path,
) -> list[Path]:
    """Download requested assets (or all system assets) from MinIO."""
    if asset_ids:
        stmt = select(Asset).where(Asset.id.in_(asset_ids))
    else:
        stmt = (
            select(Asset)
            .where(Asset.system_id == system_id)
            .order_by(Asset.created_at.asc())
        )
    result = await _maybe_await(session.execute(stmt))
    assets: list[Asset] = list(result.scalars().all())

    paths: list[Path] = []
    for asset in assets:
        try:
            tmp_path = download_asset_to_temp(
                asset.storage_key,
                suffix=_file_suffix(asset.file_name),
            )
            target = dest_dir / asset.file_name
            shutil.move(str(tmp_path), str(target))
            paths.append(target)
        except Exception:
            logger.warning("Failed to download asset %s", asset.id, exc_info=True)
    return paths


def _file_suffix(name: str) -> str:
    if "." in name:
        return "." + name.rsplit(".", 1)[-1]
    return ""


SKELETON_GENERATE_PROMPT = """\
You are a scientific paper structure analyst. Analyze the provided reference \
documents and generate a paper structure skeleton in JSON format.

The output MUST be valid JSON with this exact schema:
{{
  "sections": [
    {{
      "key": "section_key_in_snake_case",
      "title": "Section Title",
      "description": "Brief description of what this section covers"
    }}
  ],
  "change_summary": "One-line summary of the generated structure"
}}

User intent: {user_intent}

Reference documents are located at: {file_dir}
Files: {file_list}

Analyze these documents and produce a structure skeleton that would be \
appropriate for a paper based on this research. Output ONLY the JSON, \
no markdown fences, no explanation.
"""

SKELETON_REVISE_PROMPT = """\
You are a scientific paper structure analyst. Revise the existing paper \
structure skeleton based on user feedback.

Current skeleton:
{current_skeleton}

User feedback: {feedback}

Output the revised skeleton as valid JSON with this exact schema:
{{
  "sections": [
    {{
      "key": "section_key_in_snake_case",
      "title": "Section Title",
      "description": "Brief description of what this section covers"
    }}
  ],
  "change_summary": "One-line summary of what changed"
}}

Output ONLY the JSON, no markdown fences, no explanation.
"""


async def _invoke_claude_cli(prompt: str, work_dir: str | None = None) -> str:
    """Call `claude -p` and return stdout.

    Uses subprocess.run in a thread to avoid Windows asyncio subprocess limitations.
    """
    cmd = ["claude", "-p", prompt, "--output-format", "text"]
    logger.info("Invoking Claude CLI (prompt length=%d)", len(prompt))

    def _run() -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=work_dir,
            timeout=CLAUDE_CLI_TIMEOUT_SECONDS,
        )

    try:
        result = await asyncio.to_thread(_run)
    except subprocess.TimeoutExpired:
        raise AppException(
            code=ErrorCode.WORKFLOW_ERROR.value,
            message="Claude CLI timed out",
            status_code=500,
            details={"timeout_seconds": CLAUDE_CLI_TIMEOUT_SECONDS},
        )

    if result.returncode != 0:
        err_text = (result.stderr or b"").decode(errors="replace")[:500]
        logger.error("Claude CLI failed (rc=%s): %s", result.returncode, err_text)
        raise AppException(
            code=ErrorCode.WORKFLOW_ERROR.value,
            message=f"Claude CLI exited with code {result.returncode}",
            status_code=500,
            details={"stderr": err_text},
        )

    return (result.stdout or b"").decode(errors="replace").strip()


def _parse_skeleton_json(raw: str) -> dict[str, Any]:
    """Extract JSON from Claude output, tolerating markdown fences."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]  # drop opening fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return json.loads(text)


# ---------------------------------------------------------------------------
# run / complete – skeleton generation
# ---------------------------------------------------------------------------

async def run_skeleton_generation_task(
    *,
    bind: object,
    use_async_session: bool,
    workflow_id: str,
    system_id: str,
    source_asset_ids: list[str] | None = None,
    user_intent: str = "",
    broadcaster: TaskBroadcaster | None = None,
    delay_seconds: float = 0.0,
) -> None:
    if delay_seconds > 0:
        await asyncio.sleep(delay_seconds)

    if use_async_session:
        session_factory = AsyncSession(bind=bind, expire_on_commit=False)
        async with session_factory as task_session:
            await complete_skeleton_generation(
                task_session,
                workflow_id=workflow_id,
                system_id=system_id,
                source_asset_ids=source_asset_ids or [],
                user_intent=user_intent,
                broadcaster=broadcaster,
            )
        return

    with Session(bind=bind, expire_on_commit=False) as task_session:
        await complete_skeleton_generation(
            task_session,
            workflow_id=workflow_id,
            system_id=system_id,
            source_asset_ids=source_asset_ids or [],
            user_intent=user_intent,
            broadcaster=broadcaster,
        )


async def complete_skeleton_generation(
    session: SessionLike,
    *,
    workflow_id: str,
    system_id: str,
    source_asset_ids: list[str],
    user_intent: str = "",
    broadcaster: TaskBroadcaster | None = None,
) -> None:
    task_service = TaskWorkflowService(_get_task_session(session))  # type: ignore[arg-type]
    workflow_snapshot = await task_service.get_workflow_snapshot(workflow_id=workflow_id)
    if workflow_snapshot is None or workflow_snapshot.status != TaskStatus.QUEUED:
        return

    tmp_dir = Path(tempfile.mkdtemp(prefix="skeleton_gen_"))
    try:
        system = await _load_system(session, system_id)
        file_paths = await _download_assets_to_dir(
            session, source_asset_ids, system_id, tmp_dir,
        )
        if not file_paths:
            raise AppException(
                code=ErrorCode.VALIDATION_ERROR.value,
                message="No asset files available for skeleton generation",
                status_code=422,
                details={"system_id": system_id},
            )

        file_list = ", ".join(p.name for p in file_paths)
        prompt = SKELETON_GENERATE_PROMPT.format(
            user_intent=user_intent or "Generate a standard paper structure",
            file_dir=str(tmp_dir),
            file_list=file_list,
        )
        raw_output = await _invoke_claude_cli(prompt, work_dir=str(tmp_dir))
        skeleton_data = _parse_skeleton_json(raw_output)

        version = await repository.get_next_version(session, system.id)
        new_skeleton = StructureSkeleton(
            system_id=system.id,
            version=version,
            skeleton_json=skeleton_data,
            change_summary=skeleton_data.get("change_summary", "AI-generated structure"),
            source_asset_ids=source_asset_ids,
            status="draft",
        )
        session.add(new_skeleton)
        await _maybe_await(session.flush())
        await _maybe_await(session.refresh(new_skeleton))

        await append_system_workflow_event(
            task_service,
            WorkflowEventCommand(
                workflow_id=workflow_id,
                event_type=EventType.TASK_SUCCEEDED,
                message="Skeleton generation completed",
                status=TaskStatus.SUCCEEDED,
                from_state=system.status,
                to_state=system.status,
                current_state=system.status,
                current_gate=GateKey.G0.value,
                payload={
                    "skeleton_id": new_skeleton.id,
                    "skeleton_version": new_skeleton.version,
                    "skeleton_status": new_skeleton.status,
                },
                context_update={
                    "skeleton_id": new_skeleton.id,
                    "skeleton_version": new_skeleton.version,
                },
            ),
        )
        await _maybe_await(session.commit())

        if broadcaster is not None:
            await _publish_task_event(
                broadcaster,
                type=EventType.TASK_SUCCEEDED,
                task_id=workflow_snapshot.job_id,
                workflow_id=workflow_snapshot.workflow_id,
                project_id=workflow_snapshot.project_id,
                system_id=system.id,
                status=TaskStatus.SUCCEEDED,
                message="Skeleton generation completed",
                payload={
                    "skeletonId": new_skeleton.id,
                    "skeletonVersion": new_skeleton.version,
                    "skeletonStatus": new_skeleton.status,
                },
            )
    except AppException as exc:
        await _record_generation_failure(
            session=session,
            task_service=task_service,
            workflow_id=workflow_id,
            workflow_snapshot=workflow_snapshot,
            message=exc.message,
            payload={"code": exc.code, "details": exc.details},
            broadcaster=broadcaster,
        )
    except Exception:
        logger.exception("Skeleton generation failed unexpectedly")
        await _record_generation_failure(
            session=session,
            task_service=task_service,
            workflow_id=workflow_id,
            workflow_snapshot=workflow_snapshot,
            message="Skeleton generation failed unexpectedly",
            payload={"code": ErrorCode.WORKFLOW_ERROR.value, "details": {}},
            broadcaster=broadcaster,
        )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# run / complete – skeleton revision
# ---------------------------------------------------------------------------

async def run_skeleton_revision_task(
    *,
    bind: object,
    use_async_session: bool,
    workflow_id: str,
    system_id: str,
    skeleton_id: str,
    feedback: str,
    broadcaster: TaskBroadcaster | None = None,
    delay_seconds: float = 0.0,
) -> None:
    if delay_seconds > 0:
        await asyncio.sleep(delay_seconds)

    if use_async_session:
        session_factory = AsyncSession(bind=bind, expire_on_commit=False)
        async with session_factory as task_session:
            await complete_skeleton_revision(
                task_session,
                workflow_id=workflow_id,
                system_id=system_id,
                skeleton_id=skeleton_id,
                feedback=feedback,
                broadcaster=broadcaster,
            )
        return

    with Session(bind=bind, expire_on_commit=False) as task_session:
        await complete_skeleton_revision(
            task_session,
            workflow_id=workflow_id,
            system_id=system_id,
            skeleton_id=skeleton_id,
            feedback=feedback,
            broadcaster=broadcaster,
        )


async def complete_skeleton_revision(
    session: SessionLike,
    *,
    workflow_id: str,
    system_id: str,
    skeleton_id: str,
    feedback: str,
    broadcaster: TaskBroadcaster | None = None,
) -> None:
    task_service = TaskWorkflowService(_get_task_session(session))  # type: ignore[arg-type]
    workflow_snapshot = await task_service.get_workflow_snapshot(workflow_id=workflow_id)
    if workflow_snapshot is None or workflow_snapshot.status != TaskStatus.QUEUED:
        return

    try:
        system = await _load_system(session, system_id)
        old_skeleton = await _load_skeleton(session, skeleton_id)

        prompt = SKELETON_REVISE_PROMPT.format(
            current_skeleton=json.dumps(old_skeleton.skeleton_json or {}, indent=2),
            feedback=feedback,
        )
        raw_output = await _invoke_claude_cli(prompt)
        skeleton_data = _parse_skeleton_json(raw_output)

        version = await repository.get_next_version(session, system.id)
        new_skeleton = StructureSkeleton(
            system_id=system.id,
            version=version,
            skeleton_json=skeleton_data,
            change_summary=skeleton_data.get("change_summary", f"Revised: {feedback[:80]}"),
            source_asset_ids=old_skeleton.source_asset_ids or [],
            status="draft",
        )
        session.add(new_skeleton)
        await _maybe_await(session.flush())
        await _maybe_await(session.refresh(new_skeleton))

        await append_system_workflow_event(
            task_service,
            WorkflowEventCommand(
                workflow_id=workflow_id,
                event_type=EventType.TASK_SUCCEEDED,
                message="Skeleton revision completed",
                status=TaskStatus.SUCCEEDED,
                from_state=system.status,
                to_state=system.status,
                current_state=system.status,
                current_gate=GateKey.G0.value,
                payload={
                    "skeleton_id": new_skeleton.id,
                    "skeleton_version": new_skeleton.version,
                    "skeleton_status": new_skeleton.status,
                },
                context_update={
                    "skeleton_id": new_skeleton.id,
                    "skeleton_version": new_skeleton.version,
                },
            ),
        )
        await _maybe_await(session.commit())

        if broadcaster is not None:
            await _publish_task_event(
                broadcaster,
                type=EventType.TASK_SUCCEEDED,
                task_id=workflow_snapshot.job_id,
                workflow_id=workflow_snapshot.workflow_id,
                project_id=workflow_snapshot.project_id,
                system_id=system.id,
                status=TaskStatus.SUCCEEDED,
                message="Skeleton revision completed",
                payload={
                    "skeletonId": new_skeleton.id,
                    "skeletonVersion": new_skeleton.version,
                    "skeletonStatus": new_skeleton.status,
                },
            )
    except AppException as exc:
        await _record_generation_failure(
            session=session,
            task_service=task_service,
            workflow_id=workflow_id,
            workflow_snapshot=workflow_snapshot,
            message=exc.message,
            payload={"code": exc.code, "details": exc.details},
            broadcaster=broadcaster,
        )
    except Exception:
        logger.exception("Skeleton revision failed unexpectedly")
        await _record_generation_failure(
            session=session,
            task_service=task_service,
            workflow_id=workflow_id,
            workflow_snapshot=workflow_snapshot,
            message="Skeleton revision failed unexpectedly",
            payload={"code": ErrorCode.WORKFLOW_ERROR.value, "details": {}},
            broadcaster=broadcaster,
        )


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

async def _publish_task_event(
    broadcaster: TaskBroadcaster,
    *,
    type: EventType,
    task_id: str,
    workflow_id: str | None,
    project_id: str,
    system_id: str | None,
    status: TaskStatus,
    message: str,
    payload: dict[str, Any] | None = None,
) -> None:
    await broadcaster.publish(
        TaskEvent(
            type=type,
            task_id=task_id,
            workflow_id=workflow_id,
            project_id=project_id,
            system_id=system_id,
            status=status,
            message=message,
            payload=payload or {},
        )
    )


async def _record_generation_failure(
    *,
    session: SessionLike,
    task_service: TaskWorkflowService,
    workflow_id: str,
    workflow_snapshot,
    message: str,
    payload: dict[str, Any],
    broadcaster: TaskBroadcaster | None,
) -> None:
    await _maybe_await(session.rollback())
    await append_system_workflow_event(
        task_service,
        WorkflowEventCommand(
            workflow_id=workflow_id,
            event_type=EventType.TASK_FAILED,
            message=message,
            status=TaskStatus.FAILED,
            current_state=workflow_snapshot.current_state,
            current_gate=workflow_snapshot.current_gate,
            payload=payload,
            last_error=message,
        ),
    )
    await _maybe_await(session.commit())

    if broadcaster is not None:
        await _publish_task_event(
            broadcaster,
            type=EventType.TASK_FAILED,
            task_id=workflow_snapshot.job_id,
            workflow_id=workflow_snapshot.workflow_id,
            project_id=workflow_snapshot.project_id,
            system_id=workflow_snapshot.system_id,
            status=TaskStatus.FAILED,
            message=message,
            payload=payload,
        )


__all__ = [
    "SKELETON_TASK_START_DELAY_SECONDS",
    "complete_skeleton_generation",
    "complete_skeleton_revision",
    "confirm_skeleton",
    "generate_skeleton",
    "get_skeleton",
    "get_skeleton_task_session_bind",
    "list_skeletons",
    "patch_skeleton",
    "revise_skeleton",
    "run_skeleton_generation_task",
    "run_skeleton_revision_task",
]
