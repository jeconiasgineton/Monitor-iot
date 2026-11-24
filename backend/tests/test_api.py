"""Testes da API com dados FICTÍCIOS (ver app/seed_ficticio.py)."""

from fastapi.testclient import TestClient

from app.main import criar_app
from app.repositorio import RepositorioMemoria
from app.seed_ficticio import TOKEN_FICTICIO, carregar_dados_ficticios

AUTH = {"Authorization": f"Bearer {TOKEN_FICTICIO}"}


def _cliente():
    repo = carregar_dados_ficticios(RepositorioMemoria())
    return TestClient(criar_app(repo=repo)), repo


def _telemetria(seq: int, rms: float) -> dict:
    return {
        "v": 1, "seq": seq, "corrente_rms_a": rms, "corrente_max_a": rms,
        "corrente_min_a": rms, "amostras": 60, "rssi_dbm": -63, "fw": "0.1.0",
    }


def test_rejeita_sem_token():
    cliente, _ = _cliente()
    r = cliente.post("/v1/telemetria", json=_telemetria(1, 8.0))
    assert r.status_code == 401


def test_rejeita_token_invalido():
    cliente, _ = _cliente()
    r = cliente.post("/v1/telemetria", json=_telemetria(1, 8.0),
                     headers={"Authorization": "Bearer errado"})
    assert r.status_code == 401


def test_aceita_telemetria_valida():
    cliente, repo = _cliente()
    r = cliente.post("/v1/telemetria", json=_telemetria(1, 8.0), headers=AUTH)
    assert r.status_code == 200
    assert r.json()["status"] == "aceita"
    assert len(repo.telemetrias) == 1


def test_seq_duplicado_nao_grava_de_novo():
    cliente, repo = _cliente()
    cliente.post("/v1/telemetria", json=_telemetria(5, 8.0), headers=AUTH)
    r = cliente.post("/v1/telemetria", json=_telemetria(5, 8.0), headers=AUTH)
    assert r.json()["status"] == "duplicada"
    assert len(repo.telemetrias) == 1


def test_bomba_em_seco_gera_alerta_uma_vez():
    cliente, repo = _cliente()
    cliente.post("/v1/telemetria", json=_telemetria(1, 8.0), headers=AUTH)
    cliente.post("/v1/telemetria", json=_telemetria(2, 1.0), headers=AUTH)
    r = cliente.post("/v1/telemetria", json=_telemetria(3, 1.1), headers=AUTH)
    assert "bomba_em_seco" in r.json()["alertas_gerados"]

    # Nova leitura baixa não duplica o alerta já aberto
    r2 = cliente.post("/v1/telemetria", json=_telemetria(4, 1.0), headers=AUTH)
    assert r2.json()["alertas_gerados"] == []
    abertos = [a for a in repo.alertas if a.aberto and a.tipo == "bomba_em_seco"]
    assert len(abertos) == 1


def test_alerta_fecha_quando_corrente_volta_ao_normal():
    cliente, repo = _cliente()
    cliente.post("/v1/telemetria", json=_telemetria(1, 1.0), headers=AUTH)
    cliente.post("/v1/telemetria", json=_telemetria(2, 1.0), headers=AUTH)
    cliente.post("/v1/telemetria", json=_telemetria(3, 8.0), headers=AUTH)
    abertos = [a for a in repo.alertas if a.aberto and a.tipo == "bomba_em_seco"]
    assert abertos == []


def test_heartbeat_aceito_e_registrado():
    cliente, repo = _cliente()
    corpo = {"v": 1, "uptime_s": 120, "rssi_dbm": -60, "pendentes": 0, "fw": "0.1.0"}
    r = cliente.post("/v1/status", json=corpo, headers=AUTH)
    assert r.status_code == 200
    dispositivo = repo.buscar_por_token(TOKEN_FICTICIO)
    assert dispositivo.ultimo_status_epoch is not None


def test_valor_invalido_e_rejeitado():
    cliente, _ = _cliente()
    ruim = _telemetria(1, -3.0)  # corrente negativa não é válida
    r = cliente.post("/v1/telemetria", json=ruim, headers=AUTH)
    assert r.status_code == 422
