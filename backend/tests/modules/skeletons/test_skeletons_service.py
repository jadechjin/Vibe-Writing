from __future__ import annotations

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


def test_build_provider_shell_script_streams_output_to_file() -> None:
    script = service._build_provider_shell_script(
        service.SkeletonProvider.CLAUDE,
        prompt_file="F:\\tmp\\_prompt.txt",
        output_file="F:\\tmp\\_output.txt",
    )

    assert "Out-File -FilePath \"F:\\tmp\\_output.txt\" -Append -Encoding UTF8" in script
    assert "Tee-Object -Encoding UTF8" not in script
    assert "Out-String" not in script
    assert "$output =" not in script


@pytest.mark.asyncio
async def test_invoke_provider_fails_immediately_on_empty_stdout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """_invoke_provider should not auto-retry after an empty CLI output."""
    attempt_count = 0
    created_dirs: list[Path] = []

    original_mkdtemp = tempfile.mkdtemp

    def tracking_mkdtemp(**kwargs: object) -> str:
        d = original_mkdtemp(**kwargs)
        created_dirs.append(Path(d))
        return d

    async def fake_to_thread(fn: object, *_args: object, **_kwargs: object) -> int:
        nonlocal attempt_count
        if created_dirs:
            out = created_dirs[-1] / "_output.txt"
            out.write_text("", encoding="utf-8")
        attempt_count += 1
        return 0

    sleep_calls: list[int] = []

    async def fake_sleep(seconds: int) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(tempfile, "mkdtemp", tracking_mkdtemp)
    monkeypatch.setattr(service.asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(service.asyncio, "sleep", fake_sleep)

    with pytest.raises(AppException) as exc_info:
        await service._invoke_provider(service.SkeletonProvider.CLAUDE, "prompt")

    assert exc_info.value.code == ErrorCode.WORKFLOW_ERROR.value
    assert exc_info.value.message == "claude CLI returned empty output"
    assert attempt_count == 1
    assert sleep_calls == []


@pytest.mark.asyncio
async def test_invoke_provider_accepts_timeout_when_streamed_output_exists(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_file = tmp_path / "_output.txt"
    monotonic_values = iter([0.0, 0.0, service.CLAUDE_CLI_TIMEOUT_SECONDS + 1])
    sleep_calls: list[int] = []
    terminate_calls: list[float | None] = []
    original_monotonic = service.time.monotonic

    class _FakeProcess:
        returncode = None

        def poll(self) -> None:
            return None

        def terminate(self) -> None:
            terminate_calls.append(None)

        def wait(self, timeout: float | None = None) -> int:
            terminate_calls[-1] = timeout
            self.returncode = 0
            return 0

        def kill(self) -> None:
            raise AssertionError("kill should not be needed when process terminates cleanly")

    async def fake_to_thread(fn: object, *_args: object, **_kwargs: object) -> int:
        return fn()

    def fake_monotonic() -> float:
        return next(monotonic_values, original_monotonic())

    def fake_sleep(seconds: int) -> None:
        sleep_calls.append(seconds)
        output_file.write_text('{"sections":[]}', encoding="utf-8")

    monkeypatch.setattr(service.sys, "platform", "win32")
    monkeypatch.setattr(service.asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(service.time, "monotonic", fake_monotonic)
    monkeypatch.setattr(service.time, "sleep", fake_sleep)
    monkeypatch.setattr(service.subprocess, "Popen", lambda *args, **kwargs: _FakeProcess())

    raw = await service._invoke_provider(
        service.SkeletonProvider.CLAUDE,
        "prompt",
        work_dir=str(tmp_path),
    )

    assert raw == '{"sections":[]}'
    assert sleep_calls == [2]
    assert terminate_calls == [5]


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
