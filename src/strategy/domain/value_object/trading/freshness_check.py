from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FreshnessState(Enum):
    READY = "ready"
    STALE = "stale"
    MISMATCH = "mismatch"
    DEFERRED = "deferred"


@dataclass(frozen=True)
class FreshnessCheckResult:
    state: FreshnessState
    detail: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_ready(self) -> bool:
        return self.state == FreshnessState.READY

    @classmethod
    def ready(cls, detail: str = "", metadata: dict[str, Any] | None = None) -> "FreshnessCheckResult":
        return cls(
            state=FreshnessState.READY,
            detail=detail,
            metadata=dict(metadata or {}),
        )
