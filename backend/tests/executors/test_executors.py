from app.common.executors import ExecutorRequest
from app.executors import ClaudeCodeExecutor, PythonAnalysisExecutor, VisionExecutor


async def test_claude_executor_returns_result() -> None:
    executor = ClaudeCodeExecutor()
    result = await executor.run(
        ExecutorRequest(
            executor=executor.kind,
            correlation_id="corr-1",
            task_type="generate-figure-plan",
            payload={"system_id": "sys-1"},
        )
    )

    assert result.executor == executor.kind
    assert result.output["system_id"] == "sys-1"


async def test_other_executors_share_same_contract() -> None:
    request = ExecutorRequest(
        executor="vision",
        correlation_id="corr-2",
        task_type="check-asset",
        payload={"asset_id": "asset-1"},
    )

    vision_result = await VisionExecutor().run(request)
    python_result = await PythonAnalysisExecutor().run(
        request.model_copy(update={"executor": "python_analysis"})
    )

    assert vision_result.correlation_id == request.correlation_id
    assert python_result.task_type == request.task_type
