from app.common.enums import GATE_REQUIREMENTS, GateKey, TaskStatus
from app.common.executors import ExecutorRequest, ExecutorResult
from app.common.schemas import ApiResponse, JobHandle


def test_gate_mapping_is_fixed() -> None:
    assert GATE_REQUIREMENTS[GateKey.G2][0].value == "Data_Uploaded"
    assert GATE_REQUIREMENTS[GateKey.G2][1].value == "Analysis_Ready"


def test_job_handle_defaults_to_queued() -> None:
    handle = JobHandle(job_id="job-1")
    assert handle.status == TaskStatus.QUEUED


def test_api_response_is_success_by_default() -> None:
    response = ApiResponse[dict](data={"ok": True})
    assert response.success is True
    assert response.data == {"ok": True}


def test_executor_contract_round_trip() -> None:
    request = ExecutorRequest(
        executor="claude_code",
        correlation_id="corr-1",
        task_type="generate-outline",
        payload={"system_id": "sys-1"},
    )
    result = ExecutorResult(
        executor=request.executor,
        correlation_id=request.correlation_id,
        task_type=request.task_type,
        status=TaskStatus.QUEUED,
    )

    assert result.correlation_id == request.correlation_id
    assert result.task_type == request.task_type
