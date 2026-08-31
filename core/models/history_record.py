from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class HistoryRecord:
    profile: str
    start: float
    end: float
    duration: int = 0

    def __post_init__(self) -> None:
        if not self.profile:
            raise ValueError("HistoryRecord requer profile não vazio")
        if self.duration <= 0:
            self.duration = int(max(0.0, self.end - self.start))

    def to_payload(self) -> dict[str, Any]:
        return {
            "profile": self.profile,
            "start": self.start,
            "end": self.end,
            "duration": self.duration,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "HistoryRecord | None":
        try:
            return cls(
                profile=payload["profile"],
                start=payload["start"],
                end=payload["end"],
                duration=payload.get("duration", 0),
            )
        except (KeyError, ValueError, TypeError):
            return None
