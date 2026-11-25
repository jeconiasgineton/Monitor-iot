"""Testes das rotas de leitura (login por usuário) e do controle de acesso por condomínio.

Dados FICTÍCIOS: e-mails, senhas e condomínios de teste.
"""

from fastapi.testclient import TestClient

from app.main import criar_app
from app.repositorio import RepositorioMemoria
from app.seguranca import hash_senha, verificar_senha
from app.seed_ficticio import TOKEN_FICTICIO, carregar_dados_ficticios

DISPOSITIVO = "dispositivo-ficticio-001"
AUTH_DISPOSITIVO = {"Authorization": f"Bearer {TOKEN_FICTICIO}"}
SENHA_ADMIN = "senha-admin-ficticia"
SENHA_ZELADOR = "senha-zelador-ficticia"


def _preparar():
    repo = carregar_dados_ficticios(RepositorioMemoria())
    condominio = next(iter(repo.dispositivos.values())).condominio_id
    repo.criar_usuario("admin@ficticio.test", hash_senha(SENHA_ADMIN), "administrador")
    zelador = repo.criar_usuario("zelador@ficticio.test", hash_senha(SENHA_ZELADOR), "zelador")
    repo.vincular_usuario_condominio(zelador, condominio)
    outro = repo.criar_usuario("outro@ficticio.test", hash_senha(SENHA_ZELADOR), "zelador")
    repo.vincular_usuario_condominio(outro, "condominio-ficticio-outro")
    return TestClient(criar_app(repo=repo)), repo


def _login(cliente, email: str, senha: str) -> dict:
    r = cliente.post("/v1/auth/login", json={"email": email, "senha": senha})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _telemetria(seq: int, rms: float) -> dict:
    return {
        "v": 1, "seq": seq, "corrente_rms_a": rms, "corrente_max_a": rms,
        "corrente_min_a": rms, "amostras": 60, "rssi_dbm": -63, "fw": "0.1.0",
    }


def test_senha_confere_e_rejeita_erro():
    armazenado = hash_senha("correta-123456")
    assert verificar_senha("correta-123456", armazenado)
    assert not verificar_senha("errada-123456", armazenado)
    assert not verificar_senha("qualquer", "formato-invalido")


def test_login_com_senha_errada_retorna_401():
    cliente, _ = _preparar()
    r = cliente.post("/v1/auth/login", json={"email": "admin@ficticio.test", "senha": "errada"})
    assert r.status_code == 401


def test_leitura_sem_sessao_retorna_401():
    cliente, _ = _preparar()
    r = cliente.get(f"/v1/dispositivos/{DISPOSITIVO}/alertas")
    assert r.status_code == 401


def test_token_do_dispositivo_nao_serve_para_leitura():
    cliente, _ = _preparar()
    r = cliente.get(f"/v1/dispositivos/{DISPOSITIVO}/alertas", headers=AUTH_DISPOSITIVO)
    assert r.status_code == 401


def test_administrador_le_alertas_e_telemetria():
    cliente, _ = _preparar()
    auth = _login(cliente, "admin@ficticio.test", SENHA_ADMIN)
    cliente.post("/v1/telemetria", json=_telemetria(1, 8.0), headers=AUTH_DISPOSITIVO)
    cliente.post("/v1/telemetria", json=_telemetria(2, 1.0), headers=AUTH_DISPOSITIVO)
    cliente.post("/v1/telemetria", json=_telemetria(3, 1.1), headers=AUTH_DISPOSITIVO)

    r = cliente.get(f"/v1/dispositivos/{DISPOSITIVO}/alertas", headers=auth)
    assert [a["tipo"] for a in r.json()["alertas"]] == ["bomba_em_seco"]

    r = cliente.get(f"/v1/dispositivos/{DISPOSITIVO}/telemetria?limite=2", headers=auth)
    assert [l["seq"] for l in r.json()["leituras"]] == [3, 2]


def test_zelador_do_condominio_le_o_dispositivo():
    cliente, _ = _preparar()
    auth = _login(cliente, "zelador@ficticio.test", SENHA_ZELADOR)
    r = cliente.get(f"/v1/dispositivos/{DISPOSITIVO}/alertas", headers=auth)
    assert r.status_code == 200


def test_zelador_de_outro_condominio_recebe_404():
    cliente, _ = _preparar()
    auth = _login(cliente, "outro@ficticio.test", SENHA_ZELADOR)
    r = cliente.get(f"/v1/dispositivos/{DISPOSITIVO}/alertas", headers=auth)
    assert r.status_code == 404


def test_dispositivo_inexistente_retorna_404_mesmo_para_admin():
    cliente, _ = _preparar()
    auth = _login(cliente, "admin@ficticio.test", SENHA_ADMIN)
    r = cliente.get("/v1/dispositivos/nao-existe/alertas", headers=auth)
    assert r.status_code == 404


def test_sessao_expirada_nao_serve():
    cliente, repo = _preparar()
    auth = _login(cliente, "admin@ficticio.test", SENHA_ADMIN)
    repo.sessoes = {h: (uid, 0.0) for h, (uid, _) in repo.sessoes.items()}
    r = cliente.get(f"/v1/dispositivos/{DISPOSITIVO}/alertas", headers=auth)
    assert r.status_code == 401


def test_usuario_desativado_perde_acesso():
    cliente, repo = _preparar()
    auth = _login(cliente, "zelador@ficticio.test", SENHA_ZELADOR)
    for u in repo.usuarios.values():
        if u["email"] == "zelador@ficticio.test":
            u["ativo"] = False
    r = cliente.get(f"/v1/dispositivos/{DISPOSITIVO}/alertas", headers=auth)
    assert r.status_code == 401
