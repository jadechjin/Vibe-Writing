from app.common.enums import ExecutorKind
from app.executors.base import BaseExecutor


class ClaudeCodeExecutor(BaseExecutor):
    kind = ExecutorKind.CLAUDE_CODE
