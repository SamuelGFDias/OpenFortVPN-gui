import pytest

from core.models.connection_session import ConnectionSession


def test_profile_vazio_levanta_value_error():
    with pytest.raises(ValueError):
        ConnectionSession(profile="")


def test_elapsed_seconds_sem_started_at_retorna_zero():
    session = ConnectionSession(profile="matriz")
    assert session.elapsed_seconds() == 0.0


def test_elapsed_seconds_calcula_diferenca_com_now():
    session = ConnectionSession(profile="matriz", started_at=100.0)
    assert session.elapsed_seconds(now=150.0) == 50.0


def test_elapsed_seconds_nao_retorna_negativo():
    session = ConnectionSession(profile="matriz", started_at=100.0)
    assert session.elapsed_seconds(now=50.0) == 0.0


def test_round_trip_payload_preserva_dados():
    session = ConnectionSession(
        profile="matriz", pid=1234, iface="tun0", started_at=100.0
    )
    payload = session.to_payload()
    restored = ConnectionSession.from_payload(payload)

    assert restored is not None
    assert restored.profile == session.profile
    assert restored.pid == session.pid
    assert restored.iface == session.iface
    assert restored.started_at == session.started_at


def test_from_payload_sem_profile_retorna_none():
    assert ConnectionSession.from_payload({}) is None
