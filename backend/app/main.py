"""API do piloto: ingestão dos dispositivos e leitura para painel e app, com login por usuário."""

import os
import time

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from pydantic import BaseModel, Field

from .regras import Limites, avaliar_telemetria
from .repositorio import Dispositivo, RepositorioMemoria, hash_token
from .schemas import StatusIn, TelemetriaIn
from .seguranca import novo_token, verificar_senha

SESSAO_HORAS = 12


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    senha: str = Field(min_length=1, max_length=200)


def _bearer(authorization: str | None) -> str | None:
    if authorization and authorization.startswith("Bearer "):
        return authorization[len("Bearer "):].strip() or None
    return None


def criar_app(repo: RepositorioMemoria | None = None, limites: Limites | None = None) -> FastAPI:
    app = FastAPI(title="Monitoramento de bombas - piloto", version="0.1.0")
    app.state.repo = repo or RepositorioMemoria()
    app.state.limites = limites or Limites()

    def dispositivo_autenticado(authorization: str | None = Header(default=None)) -> Dispositivo:
        token = _bearer(authorization)
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token ausente")
        dispositivo = app.state.repo.buscar_por_token(token)
        if dispositivo is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
        return dispositivo

    def usuario_logado(authorization: str | None = Header(default=None)) -> dict:
        token = _bearer(authorization)
        usuario = app.state.repo.usuario_por_sessao(hash_token(token), time.time()) if token else None
        if usuario is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão inválida ou expirada")
        return usuario

    def acesso_ao_dispositivo(dispositivo_id: str, usuario: dict = Depends(usuario_logado)) -> dict:
        """Administrador vê todos os dispositivos. Zelador só vê os dos condomínios vinculados.
        Para quem não tem acesso, a resposta é 404, sem revelar se o dispositivo existe."""
        repo = app.state.repo
        condominio = repo.condominio_do_dispositivo(dispositivo_id)
        permitido = condominio is not None and (
            usuario["perfil"] == "administrador"
            or condominio in repo.condominios_do_usuario(usuario["id"])
        )
        if not permitido:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispositivo não encontrado")
        return usuario

    @app.post("/v1/auth/login", status_code=status.HTTP_200_OK)
    def login(corpo: LoginIn):
        repo = app.state.repo
        usuario = repo.usuario_por_email(corpo.email.strip().lower())
        if usuario is None or not usuario["ativo"] or not verificar_senha(corpo.senha, usuario["senha_hash"]):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha inválidos")
        token = novo_token()
        expira = time.time() + SESSAO_HORAS * 3600
        repo.criar_sessao(usuario["id"], hash_token(token), expira)
        return {"token": token, "expira_em_epoch": int(expira)}

    @app.post("/v1/telemetria", status_code=status.HTTP_200_OK)
    def receber_telemetria(
        corpo: TelemetriaIn,
        dispositivo: Dispositivo = Depends(dispositivo_autenticado),
    ):
        repo: RepositorioMemoria = app.state.repo

        # Deduplicação: seq já recebido para este dispositivo é ignorado com sucesso.
        if corpo.seq <= dispositivo.ultimo_seq:
            return {"status": "duplicada", "seq": corpo.seq}

        repo.gravar_telemetria(dispositivo, {
            "seq": corpo.seq,
            "ts": corpo.ts,
            "corrente_rms_a": corpo.corrente_rms_a,
            "corrente_max_a": corpo.corrente_max_a,
            "corrente_min_a": corpo.corrente_min_a,
            "amostras": corpo.amostras,
            "rssi_dbm": corpo.rssi_dbm,
            "fw": corpo.fw,
        })

        # O histórico já inclui a leitura gravada acima (ver repo.historico).
        historico = repo.historico(dispositivo.id)

        alertas_gerados = []
        for alerta in avaliar_telemetria(corpo.corrente_rms_a, historico, app.state.limites):
            if repo.alerta_aberto(dispositivo.id, alerta.tipo) is None:
                repo.abrir_alerta(dispositivo.id, alerta.tipo, alerta.severidade, alerta.mensagem)
                alertas_gerados.append(alerta.tipo)

        # Se a condição voltou ao normal, fecha o alerta correspondente.
        if corpo.corrente_rms_a >= app.state.limites.corrente_seca_a:
            repo.fechar_alerta(dispositivo.id, "bomba_em_seco")
        if corpo.corrente_rms_a <= app.state.limites.corrente_sobrecarga_a:
            repo.fechar_alerta(dispositivo.id, "sobrecarga")

        return {"status": "aceita", "seq": corpo.seq, "alertas_gerados": alertas_gerados}

    @app.post("/v1/status", status_code=status.HTTP_200_OK)
    def receber_status(
        corpo: StatusIn,
        dispositivo: Dispositivo = Depends(dispositivo_autenticado),
    ):
        repo: RepositorioMemoria = app.state.repo
        agora = int(time.time())
        repo.gravar_status(dispositivo, corpo.ts, agora)
        repo.fechar_alerta(dispositivo.id, "offline")
        repo.fechar_alerta(dispositivo.id, "sem_heartbeat")
        return {"status": "aceita"}

    @app.get("/v1/dispositivos/{dispositivo_id}/alertas", dependencies=[Depends(acesso_ao_dispositivo)])
    def listar_alertas(dispositivo_id: str, somente_abertos: bool = Query(default=True)):
        return {"alertas": app.state.repo.listar_alertas(dispositivo_id, somente_abertos)}

    @app.get("/v1/dispositivos/{dispositivo_id}/telemetria", dependencies=[Depends(acesso_ao_dispositivo)])
    def listar_telemetria(dispositivo_id: str, limite: int = Query(default=100, ge=1, le=1000)):
        return {"leituras": app.state.repo.listar_telemetria(dispositivo_id, limite)}

    return app


def _repositorio_padrao():
    """Usa o Postgres quando DATABASE_URL estiver definida; senão, memória com dados fictícios."""
    url = os.environ.get("DATABASE_URL")
    if url:
        from .repositorio_postgres import RepositorioPostgres
        return RepositorioPostgres(url)
    from .seed_ficticio import carregar_dados_ficticios
    return carregar_dados_ficticios(RepositorioMemoria())


app = criar_app(repo=_repositorio_padrao())
