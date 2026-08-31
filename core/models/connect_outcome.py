from dataclasses import dataclass


@dataclass(slots=True)
class ConnectOutcome:
    succeeded: bool
    exit_code: int | None = None
    message: str | None = None
