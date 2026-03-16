from __future__ import annotations

import asyncio
import enum
import json
import logging
import shutil
import subprocess
import sys
import tempfile
import time
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
    BuildPromptRequest,
    BuildPromptResponse,
    SkeletonConfirmResponse,
    SkeletonDetail,
    SkeletonGenerateRequest,
    SkeletonPatchRequest,
    SkeletonReviseRequest,
    SkeletonSummary,
)
from app.modules.tasks.service import TaskWorkflowService
from app.persistence.models.asset import Asset
from app.persistence.models.evidence import Claim, FigurePlan
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
PROVIDER_RETRY_ATTEMPTS = 2
PROVIDER_RETRY_DELAY_SECONDS = 2

# Project-level temp directory (inside git repo so Codex CLI works without --skip-git-repo-check)
_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_PROJECT_TMP = _PROJECT_ROOT / ".tmp"


def _make_project_tmpdir(prefix: str) -> Path:
    """Create a temp directory under the project root's .tmp/ folder."""
    _PROJECT_TMP.mkdir(exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=prefix, dir=str(_PROJECT_TMP)))

SessionLike = AsyncSession | Session
T = TypeVar("T")


class SkeletonProvider(str, enum.Enum):
    CLAUDE = "claude"
    CODEX = "codex"
    GEMINI = "gemini"


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
                "provider": payload.provider,
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


async def delete_skeleton(
    session: SessionLike,
    skeleton_id: str,
) -> None:
    skeleton = await _load_skeleton(session, skeleton_id)
    await repository.delete_skeleton(session, skeleton)
    await _maybe_await(session.commit())
    _cleanup_tmp_dir()


def _cleanup_tmp_dir() -> None:
    """Remove orphaned temp directories under .tmp/."""
    if not _PROJECT_TMP.exists():
        return
    for child in _PROJECT_TMP.iterdir():
        if child.is_dir() and child.name.startswith(("skeleton_", "provider_")):
            shutil.rmtree(child, ignore_errors=True)


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

    # Detect affected figure plans: orphaned section_key or version mismatch
    figure_result = await _maybe_await(session.execute(
        select(FigurePlan).where(
            FigurePlan.system_id == system_id,
            FigurePlan.section_key.isnot(None),
        )
    ))
    for plan in figure_result.scalars().all():
        if plan.section_key not in new_section_keys or plan.skeleton_version != skeleton.version:
            plan.status = "needs_review"
    await _maybe_await(session.flush())

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
                "provider": payload.provider,
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
You are a scientific research methodology and writing strategy analyst. \
Analyze the provided reference documents and generate a comprehensive \
research/writing framework skeleton in JSON format.

IMPORTANT: This is NOT a paper table-of-contents. This is a research \
thinking framework that captures HOW the research progresses — the logic \
chain from questions to evidence to conclusions. It must tightly connect \
with figure planning and data analysis strategy.

The output MUST be valid JSON with this exact schema:
{{
  "sections": [
    {{
      "key": "section_key_in_snake_case",
      "title": "Section Title",
      "description": "What this section argues and how it advances the thesis"
    }}
  ],
  "research_questions": [
    {{
      "id": "rq1",
      "question": "The core research question",
      "hypothesis": "Expected answer or hypothesis",
      "rationale": "Why this question matters to the overall argument",
      "related_sections": ["section_key_1"]
    }}
  ],
  "analysis_strategy": {{
    "methods": [
      {{
        "id": "m1",
        "name": "Method name",
        "purpose": "What this method reveals",
        "data_requirements": "What data is needed",
        "addresses_questions": ["rq1"]
      }}
    ],
    "data_flow": "Brief description of how raw data transforms into evidence"
  }},
  "figure_framework": [
    {{
      "figure_id": "fig1",
      "title": "Figure title",
      "type": "chart|diagram|table|image",
      "data_source": "Which analysis method produces this",
      "purpose": "What argument this figure supports",
      "data_question": "The specific data question this figure must answer (e.g. Is the conversion rate significantly different across temperature conditions?)",
      "importance": "high|medium|low",
      "data_preparation": "What raw data the user needs to prepare for this figure",
      "related_sections": ["section_key_1"],
      "addresses_questions": ["rq1"]
    }}
  ],
  "argument_chains": [
    {{
      "section_key": "section_key_1",
      "claim": "The core claim this section makes",
      "evidence_needed": ["fig1", "m1"],
      "reasoning_type": "deductive|inductive|comparative|causal",
      "depends_on": ["section_key_0"]
    }}
  ],
  "cross_experiment_links": [
    {{
      "from_section": "section_key_1",
      "to_section": "section_key_2",
      "relationship": "builds_on|contrasts|validates|extends",
      "shared_variables": ["variable_name"],
      "description": "How these sections connect"
    }}
  ],
  "change_summary": "One-line summary of the generated framework"
}}

Guidelines for each dimension:
- sections: Define the logical progression of the paper, not just chapter names. \
Each description should explain the argumentative role of that section.
- research_questions: Extract 2-5 core questions the research addresses. \
Link each to the sections that answer it.
- analysis_strategy: Identify the analytical methods needed, what data they \
require, and which questions they address. Describe the data-to-evidence flow.
- figure_framework: Plan key figures/tables that will serve as visual evidence. \
Each figure must link to a section and a research question. \
Rate each figure's importance (high/medium/low) based on its role in the argument. \
Describe what raw data the user needs to prepare (data_preparation) so they know \
what to collect or generate before the figure can be produced. \
Add a data_question for each figure: a specific, concrete question that the \
figure's data should answer, bridging raw data and written narrative.
- argument_chains: For each section, define what claim it makes, what evidence \
supports it, and what reasoning pattern is used.
- cross_experiment_links: Map how different sections/experiments relate to \
each other — shared variables, build-on relationships, contrasts.

User intent: {user_intent}

Reference documents are located at: {file_dir}
Files: {file_list}

Analyze these documents and produce a research/writing framework skeleton. \
所有文本内容必须使用中文输出（包括 title、description、question、hypothesis、rationale、claim、purpose 等字段），\
仅 key、id、figure_id 等标识符使用英文 snake_case。\
Output ONLY the JSON, no markdown fences, no explanation.
"""

SKELETON_REVISE_PROMPT = """\
You are a scientific research methodology and writing strategy analyst. \
Revise the existing research/writing framework skeleton based on user feedback.

The skeleton contains multiple dimensions: sections (paper structure), \
research_questions, analysis_strategy, figure_framework, argument_chains, \
and cross_experiment_links. The user feedback may target any dimension.

Current skeleton:
{current_skeleton}

User feedback: {feedback}

Output the revised skeleton as valid JSON preserving ALL dimensions. \
Keep the same schema as the input — sections, research_questions, \
analysis_strategy, figure_framework, argument_chains, cross_experiment_links, \
and change_summary. Update whichever dimensions the feedback addresses. \
Ensure cross-references (related_sections, addresses_questions, evidence_needed) \
remain consistent after changes.\
所有文本内容必须使用中文输出，仅标识符使用英文 snake_case。

Output ONLY the JSON, no markdown fences, no explanation.
"""



def _build_provider_shell_script(provider: SkeletonProvider, prompt_file: str, output_file: str) -> str:
    """Build a PowerShell script that invokes the AI CLI via a meta-prompt.

    Instead of piping the full prompt via stdin (ProcessStartInfo), this passes
    a short instruction asking the AI to read the prompt file directly.  Works
    reliably across Claude, Codex, and Gemini providers.

    Writes a sentinel file (_done.txt) on completion so the Python caller can
    poll without blocking on proc.wait().
    """
    provider_label = {"claude": "Claude Code", "codex": "Codex", "gemini": "Gemini"}[provider.value]
    done_file = str(Path(output_file).parent / "_done.txt")

    if provider is SkeletonProvider.CLAUDE:
        invoke = '& claude -p "$metaPrompt" --output-format text'
    elif provider is SkeletonProvider.CODEX:
        invoke = '& codex exec "$metaPrompt"'
    else:
        invoke = '& gemini -p "$metaPrompt" -o text'

    return (
        f'$Host.UI.RawUI.WindowTitle = "AI Generation - {provider_label}"\n'
        f'Write-Host "========================================" -ForegroundColor Cyan\n'
        f'Write-Host " AI Generation - {provider_label}" -ForegroundColor Cyan\n'
        f'Write-Host "========================================" -ForegroundColor Cyan\n'
        f'Write-Host ""\n'
        f'Write-Host "Prompt file: {prompt_file}" -ForegroundColor DarkGray\n'
        f'Write-Host "Output file: {output_file}" -ForegroundColor DarkGray\n'
        f'Write-Host ""\n'
        f'$metaPrompt = "Read the prompt file at \'{prompt_file}\' and follow ALL instructions in it exactly. Output ONLY the raw result as specified in the file, with no extra commentary."\n'
        f'try {{\n'
        f'    Write-Host "Calling {provider_label}..." -ForegroundColor Yellow\n'
        f'    Write-Host ""\n'
        f'    $output = {invoke} 2>&1 | Out-String\n'
        f'    Write-Host $output\n'
        f'    $output | Out-File -FilePath "{output_file}" -Encoding UTF8\n'
        f'}} catch {{\n'
        f'    Write-Host "Error: $_" -ForegroundColor Red\n'
        f'    $_.ToString() | Out-File -FilePath "{output_file}" -Encoding UTF8\n'
        f'}}\n'
        f'"done" | Out-File -FilePath "{done_file}" -Encoding UTF8\n'
        f'Write-Host ""\n'
        f'Write-Host "========================================" -ForegroundColor Green\n'
        f'Write-Host " Done! Window will close in 3 seconds..." -ForegroundColor Green\n'
        f'Write-Host "========================================" -ForegroundColor Green\n'
        f'Start-Sleep -Seconds 3\n'
    )


async def _invoke_provider(
    provider: SkeletonProvider,
    prompt: str,
    work_dir: str | None = None,
) -> str:
    """Call the selected provider CLI in a visible terminal window and return output."""
    logger.info("Invoking %s CLI (prompt length=%d)", provider.value, len(prompt))

    tmp_dir = Path(work_dir) if work_dir else _make_project_tmpdir("provider_")
    prompt_file = tmp_dir / "_prompt.txt"
    output_file = tmp_dir / "_output.txt"
    script_file = tmp_dir / "_run.ps1"

    prompt_file.write_text(prompt, encoding="utf-8")
    output_file.write_text("", encoding="utf-8")

    if sys.platform == "win32":
        script_content = _build_provider_shell_script(provider, str(prompt_file), str(output_file))
        script_file.write_text(script_content, encoding="utf-8")
        done_file = tmp_dir / "_done.txt"

        def _run_in_terminal() -> int:
            proc = subprocess.Popen(
                [
                    "powershell", "-ExecutionPolicy", "Bypass",
                    "-File", str(script_file),
                ],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                cwd=str(_PROJECT_ROOT),
            )
            # Poll for sentinel file instead of proc.wait() — the terminal
            # stays open (Read-Host) so we cannot wait for process exit.
            deadline = time.monotonic() + CLAUDE_CLI_TIMEOUT_SECONDS
            while time.monotonic() < deadline:
                if done_file.exists():
                    return 0
                if proc.poll() is not None:
                    # 阶段 1 修复：容错处理
                    # 如果进程退出但 output_file 存在且可解析，仍然视为成功
                    # 这样即使用户在 _done.txt 写入前关闭终端，也能继续完成
                    if output_file.exists() and output_file.stat().st_size > 0:
                        logger.info(
                            "Process exited (rc=%s) but output file exists (%d bytes), treating as success",
                            proc.returncode,
                            output_file.stat().st_size,
                        )
                        return 0
                    return proc.returncode or 1
                time.sleep(2)
            raise subprocess.TimeoutExpired(
                cmd="powershell", timeout=CLAUDE_CLI_TIMEOUT_SECONDS,
            )
    else:
        cmd = _build_provider_command_list(provider, prompt)

        def _run_in_terminal() -> int:
            with open(str(output_file), "w") as out_f:
                result = subprocess.run(
                    cmd,
                    stdout=out_f,
                    stderr=subprocess.STDOUT,
                    cwd=work_dir,
                    timeout=CLAUDE_CLI_TIMEOUT_SECONDS,
                )
            return result.returncode

    last_error: AppException | None = None
    for attempt in range(1, PROVIDER_RETRY_ATTEMPTS + 1):
        try:
            returncode = await asyncio.to_thread(_run_in_terminal)
        except subprocess.TimeoutExpired as exc:
            last_error = AppException(
                code=ErrorCode.WORKFLOW_ERROR.value,
                message=f"{provider.value} CLI timed out",
                status_code=500,
                details={
                    "provider": provider.value,
                    "timeout_seconds": CLAUDE_CLI_TIMEOUT_SECONDS,
                    "attempt": attempt,
                },
            )
            if attempt >= PROVIDER_RETRY_ATTEMPTS:
                raise last_error from exc
            logger.warning(
                "%s CLI timed out on attempt %d/%d",
                provider.value,
                attempt,
                PROVIDER_RETRY_ATTEMPTS,
            )
            await asyncio.sleep(PROVIDER_RETRY_DELAY_SECONDS)
            continue

        stdout_text = ""
        if output_file.exists():
            stdout_text = output_file.read_text(encoding="utf-8", errors="replace").strip()

        if returncode != 0:
            stderr_excerpt = stdout_text[:500]
            logger.error("%s CLI failed (rc=%s): %s", provider.value, returncode, stderr_excerpt)
            last_error = AppException(
                code=ErrorCode.WORKFLOW_ERROR.value,
                message=f"{provider.value} CLI exited with code {returncode}",
                status_code=500,
                details={
                    "provider": provider.value,
                    "stderr": stderr_excerpt,
                    "attempt": attempt,
                },
            )
            if attempt >= PROVIDER_RETRY_ATTEMPTS:
                raise last_error
            await asyncio.sleep(PROVIDER_RETRY_DELAY_SECONDS)
            continue

        if not stdout_text:
            logger.warning("%s CLI returned empty stdout on attempt %d/%d", provider.value, attempt, PROVIDER_RETRY_ATTEMPTS)
            last_error = AppException(
                code=ErrorCode.WORKFLOW_ERROR.value,
                message=f"{provider.value} CLI returned empty output",
                status_code=500,
                details={
                    "provider": provider.value,
                    "attempt": attempt,
                },
            )
            if attempt >= PROVIDER_RETRY_ATTEMPTS:
                raise last_error
            await asyncio.sleep(PROVIDER_RETRY_DELAY_SECONDS)
            continue

        return stdout_text

    if last_error is None:
        raise AppException(
            code=ErrorCode.WORKFLOW_ERROR.value,
            message="Provider invocation failed unexpectedly",
            status_code=500,
            details={"provider": provider.value},
        )
    raise last_error


def _build_provider_command_list(provider: SkeletonProvider, prompt: str) -> list[str]:
    if provider is SkeletonProvider.CLAUDE:
        return ["claude", "-p", prompt, "--output-format", "text"]
    if provider is SkeletonProvider.CODEX:
        return ["codex", "exec", prompt]
    return ["gemini", "-p", prompt, "-o", "text"]


def _parse_skeleton_json(raw: str) -> dict[str, Any]:
    """Extract JSON from provider output, tolerating markdown fences."""
    logger.info("Parsing skeleton JSON (raw length=%d)", len(raw))
    text = raw.strip().lstrip("\ufeff")  # strip BOM from PowerShell UTF8 output
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]  # drop opening fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    if not text:
        raise AppException(
            code=ErrorCode.WORKFLOW_ERROR.value,
            message="AI provider returned empty output",
            status_code=500,
            details={"reason": "empty_output"},
        )
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AppException(
            code=ErrorCode.WORKFLOW_ERROR.value,
            message="AI provider returned invalid JSON",
            status_code=500,
            details={
                "reason": "invalid_json",
                "raw_preview": text[:200],
            },
        ) from exc
    if not isinstance(data, dict):
        raise AppException(
            code=ErrorCode.WORKFLOW_ERROR.value,
            message="AI provider returned invalid skeleton payload",
            status_code=500,
            details={"reason": "invalid_payload_type", "payload_type": type(data).__name__},
        )
    if "sections" not in data:
        raise AppException(
            code=ErrorCode.WORKFLOW_ERROR.value,
            message="AI provider returned incomplete skeleton payload",
            status_code=500,
            details={"reason": "missing_required_keys", "missing_keys": ["sections"]},
        )
    return data


# ---------------------------------------------------------------------------
# Prompt building (for user review before generation)
# ---------------------------------------------------------------------------

async def build_skeleton_prompt(
    session: SessionLike,
    system_id: str,
    payload: BuildPromptRequest,
) -> BuildPromptResponse:
    await _load_system(session, system_id)
    tmp_dir = _make_project_tmpdir("skeleton_prompt_")
    try:
        file_paths = await _download_assets_to_dir(
            session, payload.source_asset_ids, system_id, tmp_dir,
        )
        if not file_paths:
            raise AppException(
                code=ErrorCode.VALIDATION_ERROR.value,
                message="No asset files available for skeleton generation",
                status_code=422,
                details={"system_id": system_id},
            )
        file_list = [p.name for p in file_paths]
        prompt = SKELETON_GENERATE_PROMPT.format(
            user_intent=payload.user_intent or "Generate a standard paper structure",
            file_dir=str(tmp_dir),
            file_list=", ".join(file_list),
        )
        return BuildPromptResponse(
            prompt=prompt,
            provider=payload.provider,
            file_dir=str(tmp_dir),
            file_list=file_list,
        )
    except AppException:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise
    except Exception:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise


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
    provider: str = SkeletonProvider.CLAUDE.value,
    custom_prompt: str | None = None,
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
                provider=provider,
                custom_prompt=custom_prompt,
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
            provider=provider,
            custom_prompt=custom_prompt,
            broadcaster=broadcaster,
        )


async def complete_skeleton_generation(
    session: SessionLike,
    *,
    workflow_id: str,
    system_id: str,
    source_asset_ids: list[str],
    user_intent: str = "",
    provider: str = SkeletonProvider.CLAUDE.value,
    custom_prompt: str | None = None,
    broadcaster: TaskBroadcaster | None = None,
) -> None:
    task_service = TaskWorkflowService(_get_task_session(session))  # type: ignore[arg-type]
    workflow_snapshot = await task_service.get_workflow_snapshot(workflow_id=workflow_id)
    if workflow_snapshot is None or workflow_snapshot.status != TaskStatus.QUEUED:
        return

    tmp_dir = _make_project_tmpdir("skeleton_gen_")
    try:
        await _publish_progress(
            broadcaster,
            workflow_id=workflow_snapshot.workflow_id,
            task_id=workflow_snapshot.job_id,
            project_id=workflow_snapshot.project_id,
            system_id=workflow_snapshot.system_id,
            stage="started",
            percentage=5,
            message="开始生成骨架",
            provider=provider,
        )
        system = await _load_system(session, system_id)

        if custom_prompt:
            # User provided an edited prompt — use it directly
            prompt = custom_prompt
            await _publish_progress(
                broadcaster,
                workflow_id=workflow_snapshot.workflow_id,
                task_id=workflow_snapshot.job_id,
                project_id=workflow_snapshot.project_id,
                system_id=workflow_snapshot.system_id,
                stage="building_prompt",
                percentage=35,
                message="使用自定义提示词",
                provider=provider,
            )
        else:
            await _publish_progress(
                broadcaster,
                workflow_id=workflow_snapshot.workflow_id,
                task_id=workflow_snapshot.job_id,
                project_id=workflow_snapshot.project_id,
                system_id=workflow_snapshot.system_id,
                stage="downloading",
                percentage=20,
                message="下载素材",
                provider=provider,
            )
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

            await _publish_progress(
                broadcaster,
                workflow_id=workflow_snapshot.workflow_id,
                task_id=workflow_snapshot.job_id,
                project_id=workflow_snapshot.project_id,
                system_id=workflow_snapshot.system_id,
                stage="building_prompt",
                percentage=35,
                message="构建提示词",
                provider=provider,
            )
            file_list = ", ".join(p.name for p in file_paths)
            prompt = SKELETON_GENERATE_PROMPT.format(
                user_intent=user_intent or "Generate a standard paper structure",
                file_dir=str(tmp_dir),
                file_list=file_list,
            )
        await _publish_progress(
            broadcaster,
            workflow_id=workflow_snapshot.workflow_id,
            task_id=workflow_snapshot.job_id,
            project_id=workflow_snapshot.project_id,
            system_id=workflow_snapshot.system_id,
            stage="calling_provider",
            percentage=70,
            message=f"调用 {provider}",
            provider=provider,
        )
        raw_output = await _invoke_provider(
            SkeletonProvider(provider),
            prompt,
            work_dir=str(tmp_dir),
        )
        logger.info(
            "Provider %s raw output (first 300 chars): %s",
            provider,
            repr(raw_output[:300]),
        )
        await _publish_progress(
            broadcaster,
            workflow_id=workflow_snapshot.workflow_id,
            task_id=workflow_snapshot.job_id,
            project_id=workflow_snapshot.project_id,
            system_id=workflow_snapshot.system_id,
            stage="parsing",
            percentage=85,
            message="解析输出",
            provider=provider,
        )
        skeleton_data = _parse_skeleton_json(raw_output)

        # 立即发送成功事件（阶段 1 修复：文件优先反馈）
        # 即使用户手动关闭终端，前端也能立即收到完成信号
        if broadcaster is not None:
            await _publish_task_event(
                broadcaster,
                type=EventType.TASK_SUCCEEDED,
                task_id=workflow_snapshot.job_id,
                workflow_id=workflow_snapshot.workflow_id,
                project_id=workflow_snapshot.project_id,
                system_id=system.id,
                status=TaskStatus.SUCCEEDED,
                message="Skeleton JSON parsed successfully",
                payload={"stage": "parsed"},
            )
            logger.info(
                "Sent immediate success event after JSON parsing for workflow_id=%s",
                workflow_snapshot.workflow_id,
            )

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
    provider: str = SkeletonProvider.CLAUDE.value,
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
                provider=provider,
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
            provider=provider,
            broadcaster=broadcaster,
        )


async def complete_skeleton_revision(
    session: SessionLike,
    *,
    workflow_id: str,
    system_id: str,
    skeleton_id: str,
    feedback: str,
    provider: str = SkeletonProvider.CLAUDE.value,
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
        raw_output = await _invoke_provider(SkeletonProvider(provider), prompt)
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
    event = TaskEvent(
        type=type,
        task_id=task_id,
        workflow_id=workflow_id,
        project_id=project_id,
        system_id=system_id,
        status=status,
        message=message,
        payload=payload or {},
    )
    logger.info(
        "Publishing task event: type=%s, workflow_id=%s, task_id=%s, status=%s",
        type,
        workflow_id,
        task_id,
        status,
    )
    await broadcaster.publish(event)


async def _publish_progress(
    broadcaster: TaskBroadcaster | None,
    *,
    workflow_id: str,
    task_id: str,
    project_id: str,
    system_id: str,
    stage: str,
    percentage: int,
    message: str,
    provider: str = "",
) -> None:
    if broadcaster is None:
        return
    await broadcaster.publish(
        TaskEvent(
            type=EventType.TASK_PROGRESS,
            task_id=task_id,
            workflow_id=workflow_id,
            project_id=project_id,
            system_id=system_id,
            status=TaskStatus.RUNNING,
            progress=percentage,
            message=message,
            payload={
                "stage": stage,
                "percentage": percentage,
                "provider": provider,
            },
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
    "build_skeleton_prompt",
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
