"""Testes das regras de alerta. Limiares FICTÍCIOS (ver app/regras.py)."""

from app.regras import Historico, Limites, avaliar_offline, avaliar_telemetria

LIMITES = Limites(corrente_seca_a=2.0, corrente_sobrecarga_a=16.0, leituras_confirmacao=2, offline_s=300)


def _avaliar(valores: list[float]):
    h = Historico()
    alertas = []
    for v in valores:
        h.adicionar(v)
        alertas = avaliar_telemetria(v, h, LIMITES)
    return alertas


def test_bomba_em_seco_exige_leituras_seguidas():
    tipos = [a.tipo for a in _avaliar([5.0, 1.0])]
    assert "bomba_em_seco" not in tipos  # só uma leitura baixa após uma normal


def test_bomba_em_seco_dispara_apos_duas_leituras_baixas():
    tipos = [a.tipo for a in _avaliar([5.0, 1.0, 1.2])]
    assert "bomba_em_seco" in tipos


def test_sobrecarga_dispara_na_hora():
    tipos = [a.tipo for a in _avaliar([17.5])]
    assert "sobrecarga" in tipos


def test_operacao_normal_nao_gera_alerta():
    assert _avaliar([8.0, 8.2, 7.9]) == []


def test_offline_quando_heartbeat_antigo():
    alerta = avaliar_offline(ultimo_status_epoch=1000, agora_epoch=1000 + 301, limites=LIMITES)
    assert alerta is not None and alerta.tipo == "offline"


def test_nao_offline_dentro_do_limite():
    assert avaliar_offline(ultimo_status_epoch=1000, agora_epoch=1200, limites=LIMITES) is None


def test_sem_heartbeat_nunca_recebido():
    alerta = avaliar_offline(ultimo_status_epoch=None, agora_epoch=1000, limites=LIMITES)
    assert alerta is not None and alerta.tipo == "sem_heartbeat"
