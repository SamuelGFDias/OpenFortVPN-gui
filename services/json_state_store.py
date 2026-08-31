import json
import os
import time
from typing import Any

from core.interfaces.state_store import AppStateStore, HistoryStore
from core.models.connection_session import ConnectionSession
from core.models.history_record import HistoryRecord
from services.runtime_paths import resolve_runtime_dir

RETENTION_SECONDS = 7 * 24 * 3600


def _load_json(path: str, default: Any) -> Any:
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


class JsonAppStateStore(AppStateStore):
    def __init__(
        self,
        state_path: str = os.path.expanduser("~/.config/openfortivpn-gui/state.json"),
        session_path: str | None = None,
    ) -> None:
        self._state_path = state_path
        self._session_path = session_path or os.path.join(
            resolve_runtime_dir(), "active_session.json"
        )

    def load_last_profile(self) -> str | None:
        data = _load_json(self._state_path, {})
        if not isinstance(data, dict):
            return None
        return data.get("last_profile")

    def save_last_profile(self, profile: str) -> None:
        data = _load_json(self._state_path, {})
        if not isinstance(data, dict):
            data = {}
        data["last_profile"] = profile
        _save_json(self._state_path, data)

    def load_active_session(self) -> ConnectionSession | None:
        data = _load_json(self._session_path, None)
        if not isinstance(data, dict):
            return None
        return ConnectionSession.from_payload(data)

    def save_active_session(self, session: ConnectionSession) -> None:
        _save_json(self._session_path, session.to_payload())

    def clear_active_session(self) -> None:
        try:
            os.remove(self._session_path)
        except OSError:
            pass


class JsonHistoryStore(HistoryStore):
    def __init__(
        self,
        history_path: str = os.path.expanduser("~/.config/openfortivpn-gui/history.json"),
    ) -> None:
        self._history_path = history_path

    def load(self) -> list[HistoryRecord]:
        raw = _load_json(self._history_path, [])
        if not isinstance(raw, list):
            return []
        records = [HistoryRecord.from_payload(item) for item in raw if isinstance(item, dict)]
        return [r for r in records if r is not None]

    def append(self, record: HistoryRecord) -> None:
        records = self.load()
        records.append(record)
        cutoff = time.time() - RETENTION_SECONDS
        records = [r for r in records if r.start >= cutoff]
        _save_json(self._history_path, [r.to_payload() for r in records])
