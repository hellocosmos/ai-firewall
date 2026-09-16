import time
from contextvars import ContextVar

from .contracts import InspectionError

INSPECTION_DEADLINE: ContextVar[float | None] = ContextVar("inspection_deadline", default=None)


def check_deadline():
  deadline = INSPECTION_DEADLINE.get()
  if deadline is not None and time.monotonic() >= deadline:
    raise InspectionError("inspection_deadline")
