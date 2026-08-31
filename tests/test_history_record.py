from core.models.history_record import HistoryRecord

import pytest


def test_profile_vazio_levanta_value_error():
    with pytest.raises(ValueError):
        HistoryRecord(profile="", start=0.0, end=10.0)


def test_duration_recalculada_quando_nao_informada():
    record = HistoryRecord(profile="matriz", start=100.0, end=160.0)
    assert record.duration == 60


def test_duration_recalculada_quando_menor_ou_igual_zero():
    record = HistoryRecord(profile="matriz", start=100.0, end=160.0, duration=0)
    assert record.duration == 60

    record_negativa = HistoryRecord(
        profile="matriz", start=100.0, end=160.0, duration=-5
    )
    assert record_negativa.duration == 60


def test_duration_informada_positiva_e_preservada():
    record = HistoryRecord(profile="matriz", start=100.0, end=160.0, duration=30)
    assert record.duration == 30


def test_round_trip_payload_preserva_dados():
    record = HistoryRecord(profile="matriz", start=100.0, end=160.0)
    payload = record.to_payload()
    restored = HistoryRecord.from_payload(payload)

    assert restored is not None
    assert restored.profile == record.profile
    assert restored.start == record.start
    assert restored.end == record.end
    assert restored.duration == record.duration


def test_from_payload_faltando_chave_obrigatoria_retorna_none():
    assert HistoryRecord.from_payload({"profile": "matriz", "start": 0.0}) is None
