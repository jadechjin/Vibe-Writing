from app.common.enums import ExecutorKind
from app.executors.base import BaseExecutor


class PythonAnalysisExecutor(BaseExecutor):
    kind = ExecutorKind.PYTHON_ANALYSIS
