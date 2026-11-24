"""Testes do repositório PostgreSQL com dados FICTÍCIOS.

Ativados somente com TEST_DATABASE_URL. ATENÇÃO: o banco indicado é apagado
(schema public é recriado). Usar apenas um banco de teste.
"""

import os
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.main import criar_app
from app.repositorio_postgres import RepositorioPostgres
from app.seed_ficticio import TOKEN_FICTICIO, carregar_dados_ficticios
from app.repositorio import RepositorioMemoria

URL = os.environ.get("TEST_DATABASE_URL")
SQL_DIR = Path(__file__).resolve().parent.parent / "sql"

pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL não definida")

AUTH = {"Authorization": f"Bearer {TOKEN_FICTICIO}"}


@pytest.fixture
def repo():
    with psycopg.connect(URL, autocommit=True) as con:
        con.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        con.execute((SQL_DIR / "schema.sql").read_text(encoding="utf-8"))
    r = RepositorioPostgres(URL)
    for d in carregar_dados_ficticios(RepositorioMemoria()).dispositivos.values():
        r.cadastrar(d)
    return r


def _cliente(repo):
    return TestClient(criar_app(repo=repo))


def _telemetria(seq: int, rms: float) -> dict:
    return {
        "v": 1, "seq": seq, "corrente_rms_a": rms, "corrente_max_a": rms,
        "corrente_min_a": rms, "amostras": 60, "rssi_dbm": -63, "fw": "0.1.0",
    }


def test_busca_dispositivo_por_token(repo):
    d = repo.buscar_por_token(TOKEN_FICTICIO)
    assert d is not None
    assert d.id == "dispositivo-ficticio-001"
    assert repo.buscar_por_token("token-errado") is None


def test_telemetria_gravada_e_seq_persistido(repo):
    cliente = _cliente(repo)
    r = cliente.post("/v1/telemetria", json=_telemetria(1, 8.0), headers=AUTH)
    assert r.json()["status"] == "aceita"
    # Nova conexão: o seq precisa ter persistido
    assert repo.buscar_por_token(TOKEN_FICTICIO).ultimo_seq == 1
    dup = cliente.post("/v1/telemetria", json=_telemetria(1, 8.0), headers=AUTH)
    assert dup.json()["status"] == "duplicada"


def test_bomba_em_seco_com_alerta_unico(repo):
    cliente = _cliente(repo)
    cliente.post("/v1/telemetria", json=_telemetria(1, 8.0), headers=AUTH)
    cliente.post("/v1/telemetria", json=_telemetria(2, 1.0), headers=AUTH)
    r = cliente.post("/v1/telemetria", json=_telemetria(3, 1.1), headers=AUTH)
    assert "bomba_em_seco" in r.json()["alertas_gerados"]
    r2 = cliente.post("/v1/telemetria", json=_telemetria(4, 1.0), headers=AUTH)
    assert r2.json()["alertas_gerados"] == []

    with psycopg.connect(URL) as con:
        n = con.execute(
            "SELECT count(*) FROM alerta WHERE tipo = 'bomba_em_seco' AND fechado_em IS NULL"
        ).fetchone()[0]
    assert n == 1


def test_alerta_fecha_quando_normaliza(repo):
    cliente = _cliente(repo)
    cliente.post("/v1/telemetria", json=_telemetria(1, 1.0), headers=AUTH)
    cliente.post("/v1/telemetria", json=_telemetria(2, 1.0), headers=AUTH)
    cliente.post("/v1/telemetria", json=_telemetria(3, 8.0), headers=AUTH)
    assert repo.alerta_aberto("dispositivo-ficticio-001", "bomba_em_seco") is None


def test_heartbeat_persistido(repo):
    cliente = _cliente(repo)
    corpo = {"v": 1, "uptime_s": 120, "rssi_dbm": -60, "pendentes": 0, "fw": "0.1.0"}
    assert cliente.post("/v1/status", json=corpo, headers=AUTH).status_code == 200
    assert repo.buscar_por_token(TOKEN_FICTICIO).ultimo_status_epoch is not None
