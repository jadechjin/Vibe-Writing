from app.common.enums import ExecutorKind, TaskStatus
from app.common.executors import ExecutorRequest, ExecutorResult


class BaseExecutor:
    kind: ExecutorKind

    async def run(self, request: ExecutorRequest) -> ExecutorResult:
        return ExecutorResult(
            executor=self.kind,
            correlation_id=request.correlation_id,
            task_type=request.task_type,
            status=TaskStatus.QUEUED,
            output=request.payload,
        )
