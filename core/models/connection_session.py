import time
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ConnectionSession:
    profile: str
    pid: int | None = None
    iface: str | None = None
    started_at: float | None = None

    def __post_init__(self) -> None:
        if not self.profile:
            raise ValueError("ConnectionSession requer profile não vazio")

    def elapsed_seconds(self, now: float | None = None) -> float:
        if self.started_at is None:
            return 0.0
        current = now if now is not None else time.time()
        return max(0.0, current - self.started_at)

    def to_payload(self) -> dict[str, Any]:
        return {
            "profile": self.profile,
            "pid": self.pid,
            "iface": self.iface,
            "started_at": self.started_at,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "ConnectionSession | None":
        profile = payload.get("profile")
        if not profile:
            return None
        return cls(
            profile=profile,
            pid=payload.get("pid"),
            iface=payload.get("iface"),
            started_at=payload.get("started_at"),
        )
