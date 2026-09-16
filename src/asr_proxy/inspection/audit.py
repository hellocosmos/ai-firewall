from __future__ import annotations

import fcntl
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


class InspectionAudit:
  def __init__(self, path: str):
    self.path = Path(path)
    self.path.parent.mkdir(parents=True, exist_ok=True)

  def record(self, verdict, *, phase: str, applied: bool = False):
    event = {"event_id": uuid4().hex, "at": datetime.now(UTC).isoformat(),
             **verdict.evidence(phase=phase, applied=applied)}
    # This is a sanitized local append log, not a production immutable audit service.
    fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as stream:
      fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
      stream.write(json.dumps(event, separators=(",", ":")) + "\n")
      stream.flush()
      fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
    return event
