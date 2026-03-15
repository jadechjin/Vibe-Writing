from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.common.enums import EventType, TaskStatus
from app.common.errors import ErrorCode
from app.common.schemas import JobHandle
from app.core.exceptions import AppException
from app.modules.skeletons import service
from app.modules.skeletons.schemas import SkeletonGenerateRequest, SkeletonReviseRequest
from app.realtime.broadcaster import TaskBroadcaster


class _DummySession:
    def __init__(self) -> None:
        self.sync_session = object()
        self.commit_calls = 0

    def commit(self) -> None:
        self.commit_calls += 1


def test_generate_request_provider_defaults_and_validation() -> None:
    payload = SkeletonGenerateRequest()
    assert payload.provider == "claude"

    explicit = SkeletonGenerateRequest(provider="gemini")
    assert explicit.provider == "gemini"

    with pytest.raises(ValidationError):
        SkeletonGenerateRequest(provider="invalid")


def test_revise_request_provider_defaults_and_validation() -> None:
    payload = SkeletonReviseRequest(skeleton_id="sk-1", feedback="revise")
    assert payload.provider == "claude"

    explicit = SkeletonReviseRequest(
        skeleton_id="sk-1",
        feedback="revise",
        provider="codex",
    )
    assert explicit.provider == "codex"

    with pytest.raises(ValidationError):
        SkeletonReviseRequest(skeleton_id="sk-1", feedback="revise", provider="invalid")


def test_parse_skeleton_json_rejects_empty_output() -> None:
    with pytest.raises(AppException) as exc_info:
        service._parse_skeleton_json("```json\n\n```")

    assert exc_info.value.code == ErrorCode.WORKFLOW_ERROR.value
    assert exc_info.value.details == {"reason": "empty_output"}


def test_parse_skeleton_json_rejects_invalid_json() -> None:
    with pytest.raises(AppException) as exc_info:
        service._parse_skeleton_json("{invalid")

    assert exc_info.value.code == ErrorCode.WORKFLOW_ERROR.value
    assert exc_info.value.details["raw_preview"] == "{invalid"


def test_parse_skeleton_json_requires_sections_key() -> None:
    with pytest.raises(AppException) as exc_info:
        service._parse_skeleton_json('{"change_summary":"x"}')

    assert exc_info.value.code == ErrorCode.WORKFLOW_ERROR.value
    assert exc_info.value.details["missing_keys"] == ["sections"]


@pytest.mark.asyncio
async def test_invoke_provider_retries_empty_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    """_invoke_provider retries when output file is empty, succeeds on second attempt."""
    attempt_count = 0
    output_contents = ["", '{"sections":[]}']
    # Track the tmp_dir created by _invoke_provider so we can write to its _output.txt
    created_dirs: list[Path] = []

    original_mkdtemp = tempfile.mkdtemp

    def tracking_mkdtemp(**kwargs: object) -> str:
        d = original_mkdtemp(**kwargs)
        created_dirs.append(Path(d))
        return d

    async def fake_to_thread(fn: object, *_args: object, **_kwargs: object) -> int:
        nonlocal attempt_count
        # Write the simulated output to the _output.txt that _invoke_provider created
        if created_dirs:
            out = created_dirs[-1] / "_output.txt"
            out.write_text(output_contents[attempt_count], encoding="utf-8")
        attempt_count += 1
        return 0

    sleep_calls: list[int] = []

    async def fake_sleep(seconds: int) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(tempfile, "mkdtemp", tracking_mkdtemp)
    monkeypatch.setattr(service.asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(service.asyncio, "sleep", fake_sleep)

    raw = await service._invoke_provider(service.SkeletonProvider.CLAUDE, "prompt")

    assert raw == '{"sections":[]}'
    assert attempt_count == 2
    assert sleep_calls == [2]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("provider", "expected_cmd"),
    [
        (
            "claude",
            ["claude", "-p", "prompt", "--output-format", "text"],
        ),
        (
            "codex",
            ["codex", "exec", "prompt"],
        ),
        (
            "gemini",
            ["gemini", "-p", "prompt", "-o", "text"],
        ),
    ],
)
async def test_invoke_provider_builds_expected_command(
    monkeypatch: pytest.MonkeyPatch,
    provider: str,
    expected_cmd: list[str],
) -> None:
    """On non-Windows, _build_provider_command_list produces the expected argv."""
    # We test the command-list builder directly instead of going through _invoke_provider
    # because _invoke_provider on Windows uses PowerShell scripts, not subprocess.run.
    cmd = service._build_provider_command_list(service.SkeletonProvider(provider), "prompt")
    assert cmd == expected_cmd


@pytest.mark.asyncio
async def test_publish_progress_emits_running_task_progress_event() -> None:
    broadcaster = TaskBroadcaster(max_queue_size=4)
    sub_id = await broadcaster.subscribe()

    await service._publish_progress(
        broadcaster,
        workflow_id="wf-1",
        task_id="task-1",
        project_id="project-1",
        system_id="system-1",
        stage="building_prompt",
        percentage=35,
        message="构建提示词",
        provider="gemini",
    )

    async with broadcaster._lock:
        queue = broadcaster._subscribers[sub_id]

    event = queue.get_nowait()
    assert event.type == EventType.TASK_PROGRESS
    assert event.status == TaskStatus.RUNNING
    assert event.progress == 35
    assert event.payload == {
        "stage": "building_prompt",
        "percentage": 35,
        "provider": "gemini",
    }


@pytest.mark.asyncio
async def test_generate_skeleton_stores_provider_in_workflow_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def fake_load_system(_session: object, _system_id: str) -> SimpleNamespace:
        return SimpleNamespace(id="system-1", project_id="project-1", status="Draft")

    async def fake_start_workflow(_task_service: object, command: object) -> SimpleNamespace:
        captured["context"] = command.context
        return SimpleNamespace(
            handle=JobHandle(
                workflow_id="wf-1",
                job_id="task-1",
                status=TaskStatus.QUEUED,
            )
        )

    monkeypatch.setattr(service, "_load_system", fake_load_system)
    monkeypatch.setattr(service, "TaskWorkflowService", lambda _session: object())
    monkeypatch.setattr(service, "start_system_workflow", fake_start_workflow)

    session = _DummySession()
    payload = SkeletonGenerateRequest(provider="gemini")

    await service.generate_skeleton(session, "system-1", payload)

    assert captured["context"] == {
        "source_asset_ids": [],
        "user_intent": "",
        "provider": "gemini",
    }
    assert session.commit_calls == 1


@pytest.mark.asyncio
async def test_revise_skeleton_stores_provider_in_workflow_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def fake_load_system(_session: object, _system_id: str) -> SimpleNamespace:
        return SimpleNamespace(id="system-1", project_id="project-1", status="Draft")

    async def fake_load_skeleton(_session: object, skeleton_id: str) -> SimpleNamespace:
        return SimpleNamespace(id=skeleton_id)

    async def fake_start_workflow(_task_service: object, command: object) -> SimpleNamespace:
        captured["context"] = command.context
        return SimpleNamespace(
            handle=JobHandle(
                workflow_id="wf-1",
                job_id="task-1",
                status=TaskStatus.QUEUED,
            )
        )

    monkeypatch.setattr(service, "_load_system", fake_load_system)
    monkeypatch.setattr(service, "_load_skeleton", fake_load_skeleton)
    monkeypatch.setattr(service, "TaskWorkflowService", lambda _session: object())
    monkeypatch.setattr(service, "start_system_workflow", fake_start_workflow)

    session = _DummySession()
    payload = SkeletonReviseRequest(
        skeleton_id="skeleton-1",
        feedback="revise",
        provider="codex",
    )

    await service.revise_skeleton(session, "system-1", payload)

    assert captured["context"] == {
        "skeleton_id": "skeleton-1",
        "feedback": "revise",
        "provider": "codex",
    }
    assert session.commit_calls == 1
