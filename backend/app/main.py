"""API do piloto: recebe telemetria e heartbeat dos dispositivos via HTTPS."""

import hmac
import os
import time

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status

from .regras import Limites, avaliar_telemetria
from .repositorio import Dispositivo, RepositorioMemoria
from .schemas import StatusIn, TelemetriaIn


def criar_app(repo: RepositorioMemoria | None = None, limites: Limites | None = None) -> FastAPI:
    app = FastAPI(title="Monitoramento de bombas - piloto", version="0.1.0")
    app.state.repo = repo or RepositorioMemoria()
    app.state.limites = limites or Limites()

    def dispositivo_autenticado(authorization: str | None = Header(default=None)) -> Dispositivo:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token ausente")
        token = authorization[len("Bearer "):].strip()
        dispositivo = app.state.repo.buscar_por_token(token)
        if dispositivo is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
        return dispositivo

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

    def leitura_autorizada(authorization: str | None = Header(default=None)) -> None:
        """Leitura para painel e app. Usa API_LEITURA_TOKEN; sem essa variável, a leitura fica fechada."""
        esperado = os.environ.get("API_LEITURA_TOKEN")
        if not esperado:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                                detail="Leitura não configurada")
        recebido = ""
        if authorization and authorization.startswith("Bearer "):
            recebido = authorization[len("Bearer "):].strip()
        # Comparação em bytes: compare_digest não aceita texto com caracteres não ASCII.
        if not hmac.compare_digest(recebido.encode("utf-8"), esperado.encode("utf-8")):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de leitura inválido")

    @app.get("/v1/dispositivos/{dispositivo_id}/alertas", dependencies=[Depends(leitura_autorizada)])
    def listar_alertas(dispositivo_id: str, somente_abertos: bool = Query(default=True)):
        return {"alertas": app.state.repo.listar_alertas(dispositivo_id, somente_abertos)}

    @app.get("/v1/dispositivos/{dispositivo_id}/telemetria", dependencies=[Depends(leitura_autorizada)])
    def listar_telemetria(dispositivo_id: str, limite: int = Query(default=100, ge=1, le=1000)):
        return {"leituras": app.state.repo.listar_telemetria(dispositivo_id, limite)}

    return app


def _repositorio_padrao():
    """Usa o Postgres quando DATABASE_URL estiver definida; senão, memória com dados fictícios."""
    import os

    url = os.environ.get("DATABASE_URL")
    if url:
        from .repositorio_postgres import RepositorioPostgres
        return RepositorioPostgres(url)
    from .seed_ficticio import carregar_dados_ficticios
    return carregar_dados_ficticios(RepositorioMemoria())


app = criar_app(repo=_repositorio_padrao())
