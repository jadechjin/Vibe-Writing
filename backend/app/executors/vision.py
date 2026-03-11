from app.common.enums import ExecutorKind
from app.executors.base import BaseExecutor


class VisionExecutor(BaseExecutor):
    kind = ExecutorKind.VISION
