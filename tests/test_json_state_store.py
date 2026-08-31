import json
import time

from core.models.connection_session import ConnectionSession
from core.models.history_record import HistoryRecord
from services.json_state_store import JsonAppStateStore, JsonHistoryStore

DAY = 24 * 3600


def test_last_profile_round_trip(tmp_path):
    store = JsonAppStateStore(
        state_path=str(tmp_path / "state.json"),
        session_path=str(tmp_path / "session.json"),
    )

    assert store.load_last_profile() is None

    store.save_last_profile("matriz")

    assert store.load_last_profile() == "matriz"


def test_save_last_profile_preserva_outros_campos_existentes(tmp_path):
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps({"outro_campo": "valor"}))
    store = JsonAppStateStore(state_path=str(state_path), session_path=str(tmp_path / "session.json"))

    store.save_last_profile("filial")

    data = json.loads(state_path.read_text())
    assert data["last_profile"] == "filial"
    assert data["outro_campo"] == "valor"


def test_active_session_save_load_clear(tmp_path):
    store = JsonAppStateStore(
        state_path=str(tmp_path / "state.json"),
        session_path=str(tmp_path / "session.json"),
    )

    assert store.load_active_session() is None

    session = ConnectionSession(profile="matriz", pid=123, iface="tun0", started_at=100.0)
    store.save_active_session(session)

    loaded = store.load_active_session()
    assert loaded is not None
    assert loaded.profile == "matriz"
    assert loaded.pid == 123
    assert loaded.iface == "tun0"
    assert loaded.started_at == 100.0

    store.clear_active_session()

    assert store.load_active_session() is None


def test_clear_active_session_sem_arquivo_nao_levanta_erro(tmp_path):
    store = JsonAppStateStore(
        state_path=str(tmp_path / "state.json"),
        session_path=str(tmp_path / "session-inexistente.json"),
    )

    store.clear_active_session()  # não deve levantar


def test_state_json_corrompido_cai_pro_default(tmp_path):
    state_path = tmp_path / "state.json"
    state_path.write_text("{ isso nao eh json valido")
    store = JsonAppStateStore(state_path=str(state_path), session_path=str(tmp_path / "session.json"))

    assert store.load_last_profile() is None


def test_session_json_corrompido_cai_pro_default(tmp_path):
    session_path = tmp_path / "session.json"
    session_path.write_text("não é json")
    store = JsonAppStateStore(state_path=str(tmp_path / "state.json"), session_path=str(session_path))

    assert store.load_active_session() is None


def test_history_append_e_load_round_trip(tmp_path):
    history_path = tmp_path / "history.json"
    store = JsonHistoryStore(history_path=str(history_path))

    assert store.load() == []

    now = time.time()
    record = HistoryRecord(profile="matriz", start=now, end=now + 60)
    store.append(record)

    records = store.load()
    assert len(records) == 1
    assert records[0].profile == "matriz"
    assert records[0].start == record.start
    assert records[0].end == record.end
    assert records[0].duration == 60


def test_history_purga_registros_com_mais_de_7_dias(tmp_path):
    history_path = tmp_path / "history.json"
    now = time.time()

    old_record = {
        "profile": "antigo",
        "start": now - 8 * DAY,
        "end": now - 8 * DAY + 60,
        "duration": 60,
    }
    recent_record = {
        "profile": "recente",
        "start": now - DAY,
        "end": now - DAY + 60,
        "duration": 60,
    }
    history_path.write_text(json.dumps([old_record, recent_record]))

    store = JsonHistoryStore(history_path=str(history_path))
    # append de um novo registro dispara a purga
    store.append(HistoryRecord(profile="novo", start=now, end=now + 30))

    profiles = {r.profile for r in store.load()}
    assert profiles == {"recente", "novo"}
    assert "antigo" not in profiles


def test_history_json_corrompido_cai_pro_default(tmp_path):
    history_path = tmp_path / "history.json"
    history_path.write_text("[ nao eh json")

    store = JsonHistoryStore(history_path=str(history_path))

    assert store.load() == []


def test_history_json_nao_lista_cai_pro_default(tmp_path):
    history_path = tmp_path / "history.json"
    history_path.write_text(json.dumps({"nao": "e uma lista"}))

    store = JsonHistoryStore(history_path=str(history_path))

    assert store.load() == []
