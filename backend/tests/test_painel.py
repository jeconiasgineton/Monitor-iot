"""Testes da listagem de dispositivos, troca de senha e da página do painel. Dados FICTÍCIOS."""

from fastapi.testclient import TestClient

from app.main import criar_app
from app.repositorio import RepositorioMemoria
from app.seguranca import hash_senha
from app.seed_ficticio import carregar_dados_ficticios

SENHA = "senha-ficticia-123"


def _preparar():
    repo = carregar_dados_ficticios(RepositorioMemoria())
    condominio = next(iter(repo.dispositivos.values())).condominio_id
    admin = repo.criar_usuario("admin@ficticio.test", hash_senha(SENHA), "administrador")
    zelador = repo.criar_usuario("zelador@ficticio.test", hash_senha(SENHA), "zelador")
    repo.vincular_usuario_condominio(zelador, condominio)
    outro = repo.criar_usuario("outro@ficticio.test", hash_senha(SENHA), "zelador")
    repo.vincular_usuario_condominio(outro, "condominio-ficticio-outro")
    return TestClient(criar_app(repo=repo)), repo


def _login(cliente, email):
    r = cliente.post("/v1/auth/login", json={"email": email, "senha": SENHA})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_administrador_lista_todos_os_dispositivos():
    cliente, _ = _preparar()
    r = cliente.get("/v1/dispositivos", headers=_login(cliente, "admin@ficticio.test"))
    ids = [d["id"] for d in r.json()["dispositivos"]]
    assert ids == ["dispositivo-ficticio-001"]


def test_zelador_vinculado_ve_o_dispositivo():
    cliente, _ = _preparar()
    r = cliente.get("/v1/dispositivos", headers=_login(cliente, "zelador@ficticio.test"))
    assert [d["id"] for d in r.json()["dispositivos"]] == ["dispositivo-ficticio-001"]


def test_zelador_de_outro_condominio_nao_ve_dispositivos():
    cliente, _ = _preparar()
    r = cliente.get("/v1/dispositivos", headers=_login(cliente, "outro@ficticio.test"))
    assert r.json()["dispositivos"] == []


def test_listar_dispositivos_sem_sessao_retorna_401():
    cliente, _ = _preparar()
    assert cliente.get("/v1/dispositivos").status_code == 401


def test_troca_de_senha_exige_senha_atual_correta():
    cliente, _ = _preparar()
    auth = _login(cliente, "admin@ficticio.test")
    r = cliente.post("/v1/auth/senha", headers=auth,
                     json={"senha_atual": "errada", "senha_nova": "nova-senha-123"})
    assert r.status_code == 401


def test_troca_de_senha_encerra_sessoes_e_aceita_a_nova():
    cliente, _ = _preparar()
    auth = _login(cliente, "admin@ficticio.test")
    r = cliente.post("/v1/auth/senha", headers=auth,
                     json={"senha_atual": SENHA, "senha_nova": "nova-senha-123"})
    assert r.status_code == 200
    # A sessão antiga deixa de valer.
    assert cliente.get("/v1/dispositivos", headers=auth).status_code == 401
    # Senha antiga não entra mais; a nova entra.
    assert cliente.post("/v1/auth/login", json={"email": "admin@ficticio.test", "senha": SENHA}).status_code == 401
    assert cliente.post("/v1/auth/login", json={"email": "admin@ficticio.test", "senha": "nova-senha-123"}).status_code == 200


def test_senha_nova_curta_retorna_422():
    cliente, _ = _preparar()
    auth = _login(cliente, "admin@ficticio.test")
    r = cliente.post("/v1/auth/senha", headers=auth,
                     json={"senha_atual": SENHA, "senha_nova": "curta"})
    assert r.status_code == 422


def test_pagina_do_painel_e_servida():
    cliente, _ = _preparar()
    r = cliente.get("/painel")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "Monitoramento de bombas" in r.text
