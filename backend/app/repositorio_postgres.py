"""Repositório do piloto em PostgreSQL (Neon).

Mesma interface de RepositorioMemoria. Usa uma conexão curta por operação,
o que combina com a Vercel (funções que sobem e descem a cada requisição).

Antes de usar: aplicar backend/sql/schema.sql e, se o TimescaleDB estiver
disponível, backend/sql/timescale.sql.
"""

from datetime import datetime, timezone

import psycopg

from .regras import Historico
from .repositorio import Dispositivo


class RepositorioPostgres:
    def __init__(self, url: str):
        self.url = url

    def _conexao(self, autocommit: bool = True) -> psycopg.Connection:
        return psycopg.connect(self.url, autocommit=autocommit)

    # ---------- Cadastro ----------
    def cadastrar(self, dispositivo: Dispositivo) -> None:
        """Insere condomínio, casa, bomba e dispositivo, sem sobrescrever o que já existe."""
        with self._conexao() as con:
            con.execute(
                "INSERT INTO condominio (id, nome) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
                (dispositivo.condominio_id, dispositivo.condominio_id),
            )
            con.execute(
                "INSERT INTO casa_maquinas (id, condominio_id) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
                (dispositivo.casa_id, dispositivo.condominio_id),
            )
            con.execute(
                "INSERT INTO bomba (id, casa_id) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
                (dispositivo.bomba_id, dispositivo.casa_id),
            )
            con.execute(
                """INSERT INTO dispositivo (id, bomba_id, token_hash, ativo)
                   VALUES (%s, %s, %s, %s) ON CONFLICT (id) DO NOTHING""",
                (dispositivo.id, dispositivo.bomba_id, dispositivo.token_hash, dispositivo.ativo),
            )

    # ---------- Leitura de dispositivo ----------
    def buscar_por_token(self, token: str) -> Dispositivo | None:
        from .repositorio import hash_token

        with self._conexao() as con:
            linha = con.execute(
                """SELECT d.id, b.casa_id, c.condominio_id, d.bomba_id, d.token_hash,
                          d.ativo, d.ultimo_seq, d.ultimo_status
                   FROM dispositivo d
                   JOIN bomba b ON b.id = d.bomba_id
                   JOIN casa_maquinas c ON c.id = b.casa_id
                   WHERE d.token_hash = %s AND d.ativo = TRUE""",
                (hash_token(token),),
            ).fetchone()
        if linha is None:
            return None
        (id_, casa_id, condominio_id, bomba_id, token_hash, ativo, ultimo_seq, ultimo_status) = linha
        return Dispositivo(
            id=id_,
            condominio_id=condominio_id,
            casa_id=casa_id,
            bomba_id=bomba_id,
            token_hash=token_hash,
            ativo=ativo,
            ultimo_seq=ultimo_seq,
            ultimo_status_epoch=int(ultimo_status.timestamp()) if ultimo_status else None,
        )

    def historico(self, dispositivo_id: str) -> Historico:
        """Últimas leituras de corrente, em ordem cronológica. Inclui a última gravada."""
        with self._conexao() as con:
            linhas = con.execute(
                """SELECT corrente_rms_a FROM telemetria
                   WHERE dispositivo_id = %s
                   ORDER BY recebido_em DESC, seq DESC
                   LIMIT 10""",
                (dispositivo_id,),
            ).fetchall()
        valores = [float(l[0]) for l in reversed(linhas)]
        return Historico(valores=valores, tamanho=10)

    # ---------- Escrita ----------
    def gravar_telemetria(self, dispositivo: Dispositivo, dados: dict) -> None:
        medido_em = (
            datetime.fromtimestamp(dados["ts"], tz=timezone.utc) if dados.get("ts") else None
        )
        with self._conexao(autocommit=False) as con:
            con.execute(
                """INSERT INTO telemetria
                   (dispositivo_id, medido_em, seq, corrente_rms_a, corrente_max_a,
                    corrente_min_a, amostras, rssi_dbm, fw)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    dispositivo.id, medido_em, dados["seq"], dados["corrente_rms_a"],
                    dados["corrente_max_a"], dados["corrente_min_a"], dados["amostras"],
                    dados["rssi_dbm"], dados["fw"],
                ),
            )
            con.execute(
                "UPDATE dispositivo SET ultimo_seq = %s WHERE id = %s",
                (dados["seq"], dispositivo.id),
            )
            con.commit()
        dispositivo.ultimo_seq = dados["seq"]

    def gravar_status(self, dispositivo: Dispositivo, ts_epoch: int | None, agora_epoch: int) -> None:
        momento = ts_epoch if ts_epoch is not None else agora_epoch
        with self._conexao() as con:
            con.execute(
                "UPDATE dispositivo SET ultimo_status = to_timestamp(%s) WHERE id = %s",
                (momento, dispositivo.id),
            )
        dispositivo.ultimo_status_epoch = momento

    # ---------- Alertas ----------
    def alerta_aberto(self, dispositivo_id: str, tipo: str):
        with self._conexao() as con:
            return con.execute(
                """SELECT id FROM alerta
                   WHERE dispositivo_id = %s AND tipo = %s AND fechado_em IS NULL""",
                (dispositivo_id, tipo),
            ).fetchone()

    def abrir_alerta(self, dispositivo_id: str, tipo: str, severidade: str, mensagem: str):
        # O índice único parcial impede dois alertas abertos do mesmo tipo.
        with self._conexao() as con:
            return con.execute(
                """INSERT INTO alerta (dispositivo_id, tipo, severidade, mensagem)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (dispositivo_id, tipo) WHERE fechado_em IS NULL DO NOTHING
                   RETURNING id""",
                (dispositivo_id, tipo, severidade, mensagem),
            ).fetchone()

    def fechar_alerta(self, dispositivo_id: str, tipo: str) -> None:
        with self._conexao() as con:
            con.execute(
                """UPDATE alerta SET fechado_em = now()
                   WHERE dispositivo_id = %s AND tipo = %s AND fechado_em IS NULL""",
                (dispositivo_id, tipo),
            )

    # ---------- Leitura para painel e app ----------
    def dispositivo_existe(self, dispositivo_id: str) -> bool:
        with self._conexao() as con:
            linha = con.execute(
                "SELECT 1 FROM dispositivo WHERE id = %s", (dispositivo_id,)
            ).fetchone()
        return linha is not None

    def listar_alertas(self, dispositivo_id: str, somente_abertos: bool = True) -> list[dict]:
        filtro = "AND fechado_em IS NULL" if somente_abertos else ""
        with self._conexao() as con:
            linhas = con.execute(
                f"""SELECT id, tipo, severidade, mensagem, aberto_em, fechado_em
                    FROM alerta WHERE dispositivo_id = %s {filtro}
                    ORDER BY aberto_em DESC LIMIT 200""",
                (dispositivo_id,),
            ).fetchall()
        return [
            {"id": l[0], "tipo": l[1], "severidade": l[2], "mensagem": l[3],
             "aberto_em": l[4].isoformat(), "fechado_em": l[5].isoformat() if l[5] else None}
            for l in linhas
        ]

    def listar_telemetria(self, dispositivo_id: str, limite: int = 100) -> list[dict]:
        with self._conexao() as con:
            linhas = con.execute(
                """SELECT recebido_em, medido_em, seq, corrente_rms_a, corrente_max_a, corrente_min_a
                   FROM telemetria WHERE dispositivo_id = %s
                   ORDER BY recebido_em DESC, seq DESC LIMIT %s""",
                (dispositivo_id, limite),
            ).fetchall()
        return [
            {"recebido_em": l[0].isoformat(),
             "medido_em": l[1].isoformat() if l[1] else None,
             "seq": l[2], "corrente_rms_a": float(l[3]),
             "corrente_max_a": float(l[4]), "corrente_min_a": float(l[5])}
            for l in linhas
        ]
