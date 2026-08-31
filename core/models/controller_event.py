from dataclasses import dataclass


@dataclass(slots=True)
class ControllerEvent:
    kind: str  # "connected" | "disconnected" | "connect_failed" | "cancelled"
    duration_seconds: float | None = None
    reason: str | None = None
