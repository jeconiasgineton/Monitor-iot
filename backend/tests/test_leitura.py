"""Testes das rotas de leitura para painel e app, com dados FICTÍCIOS."""

from fastapi.testclient import TestClient

from app.main import criar_app
from app.repositorio import RepositorioMemoria
from app.seed_ficticio import TOKEN_FICTICIO, carregar_dados_ficticios

TOKEN_LEITURA = "LEITURA-FICTICIA-NAO-USAR-EM-PRODUCAO"
AUTH_DISPOSITIVO = {"Authorization": f"Bearer {TOKEN_FICTICIO}"}
AUTH_LEITURA = {"Authorization": f"Bearer {TOKEN_LEITURA}"}
DISPOSITIVO = "dispositivo-ficticio-001"


def _cliente(monkeypatch, com_token: bool = True):
    if com_token:
        monkeypatch.setenv("API_LEITURA_TOKEN", TOKEN_LEITURA)
    else:
        monkeypatch.delenv("API_LEITURA_TOKEN", raising=False)
    repo = carregar_dados_ficticios(RepositorioMemoria())
    return TestClient(criar_app(repo=repo)), repo


def _telemetria(seq: int, rms: float) -> dict:
    return {
        "v": 1, "seq": seq, "corrente_rms_a": rms, "corrente_max_a": rms,
        "corrente_min_a": rms, "amostras": 60, "rssi_dbm": -63, "fw": "0.1.0",
    }


def test_leitura_fechada_sem_variavel(monkeypatch):
    cliente, _ = _cliente(monkeypatch, com_token=False)
    r = cliente.get(f"/v1/dispositivos/{DISPOSITIVO}/alertas", headers=AUTH_LEITURA)
    assert r.status_code == 503


def test_leitura_rejeita_token_do_dispositivo(monkeypatch):
    cliente, _ = _cliente(monkeypatch)
    r = cliente.get(f"/v1/dispositivos/{DISPOSITIVO}/alertas", headers=AUTH_DISPOSITIVO)
    assert r.status_code == 401


def test_alertas_abertos_e_historico(monkeypatch):
    cliente, _ = _cliente(monkeypatch)
    cliente.post("/v1/telemetria", json=_telemetria(1, 8.0), headers=AUTH_DISPOSITIVO)
    cliente.post("/v1/telemetria", json=_telemetria(2, 1.0), headers=AUTH_DISPOSITIVO)
    cliente.post("/v1/telemetria", json=_telemetria(3, 1.1), headers=AUTH_DISPOSITIVO)

    r = cliente.get(f"/v1/dispositivos/{DISPOSITIVO}/alertas", headers=AUTH_LEITURA)
    tipos = [a["tipo"] for a in r.json()["alertas"]]
    assert tipos == ["bomba_em_seco"]

    r = cliente.get(f"/v1/dispositivos/{DISPOSITIVO}/telemetria?limite=2", headers=AUTH_LEITURA)
    leituras = r.json()["leituras"]
    assert [l["seq"] for l in leituras] == [3, 2]


def test_alerta_fechado_some_do_filtro_de_abertos(monkeypatch):
    cliente, _ = _cliente(monkeypatch)
    cliente.post("/v1/telemetria", json=_telemetria(1, 1.0), headers=AUTH_DISPOSITIVO)
    cliente.post("/v1/telemetria", json=_telemetria(2, 1.0), headers=AUTH_DISPOSITIVO)
    cliente.post("/v1/telemetria", json=_telemetria(3, 8.0), headers=AUTH_DISPOSITIVO)

    abertos = cliente.get(f"/v1/dispositivos/{DISPOSITIVO}/alertas", headers=AUTH_LEITURA).json()
    todos = cliente.get(f"/v1/dispositivos/{DISPOSITIVO}/alertas?somente_abertos=false",
                        headers=AUTH_LEITURA).json()
    assert abertos["alertas"] == []
    assert len(todos["alertas"]) == 1
    assert todos["alertas"][0]["aberto"] is False


def test_dispositivo_inexistente_retorna_404(monkeypatch):
    cliente, _ = _cliente(monkeypatch)
    for rota in ("alertas", "telemetria"):
        r = cliente.get(f"/v1/dispositivos/nao-existe/{rota}", headers=AUTH_LEITURA)
        assert r.status_code == 404
    # A autenticação vem antes: sem token válido continua 401, sem revelar existência.
    r = cliente.get("/v1/dispositivos/nao-existe/alertas", headers=AUTH_DISPOSITIVO)
    assert r.status_code == 401


def test_dispositivo_existente_sem_dados_retorna_lista_vazia(monkeypatch):
    cliente, _ = _cliente(monkeypatch)
    r = cliente.get(f"/v1/dispositivos/{DISPOSITIVO}/alertas", headers=AUTH_LEITURA)
    assert r.status_code == 200 and r.json() == {"alertas": []}


def test_token_de_leitura_com_caractere_nao_ascii_nao_gera_500(monkeypatch):
    # Regressão: variável com acento causava TypeError em compare_digest (500 na Vercel).
    monkeypatch.setenv("API_LEITURA_TOKEN", "leitura-çãö")
    repo = carregar_dados_ficticios(RepositorioMemoria())
    cliente = TestClient(criar_app(repo=repo))
    r = cliente.get(f"/v1/dispositivos/{DISPOSITIVO}/alertas",
                    headers={"Authorization": "Bearer leitura-errada"})
    assert r.status_code == 401
