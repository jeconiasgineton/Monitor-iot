"""Repositório do piloto.

RepositorioMemoria é a implementação usada em testes e no desenvolvimento local.
A implementação para Neon (PostgreSQL + TimescaleDB) usa backend/sql/schema.sql
e ainda não foi escrita (ver backend/README.md, pendências).
"""

import hashlib
from dataclasses import dataclass, field

from .regras import Historico


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass
class Dispositivo:
    id: str
    condominio_id: str
    casa_id: str
    bomba_id: str
    token_hash: str
    ativo: bool = True
    ultimo_seq: int = -1
    ultimo_status_epoch: int | None = None


@dataclass
class AlertaAberto:
    id: int
    dispositivo_id: str
    tipo: str
    severidade: str
    mensagem: str
    aberto: bool = True


@dataclass
class RepositorioMemoria:
    dispositivos: dict[str, Dispositivo] = field(default_factory=dict)
    historicos: dict[str, Historico] = field(default_factory=dict)
    telemetrias: list[dict] = field(default_factory=list)
    alertas: list[AlertaAberto] = field(default_factory=list)
    _proximo_id: int = 1
    usuarios: dict[int, dict] = field(default_factory=dict)
    usuario_condominios: set[tuple[int, str]] = field(default_factory=set)
    sessoes: dict[str, tuple[int, float]] = field(default_factory=dict)
    _proximo_usuario: int = 1

    def cadastrar(self, dispositivo: Dispositivo) -> None:
        self.dispositivos[dispositivo.token_hash] = dispositivo

    def buscar_por_token(self, token: str) -> Dispositivo | None:
        d = self.dispositivos.get(hash_token(token))
        return d if d and d.ativo else None

    def historico(self, dispositivo_id: str) -> Historico:
        return self.historicos.setdefault(dispositivo_id, Historico())

    def gravar_telemetria(self, dispositivo: Dispositivo, dados: dict) -> None:
        self.telemetrias.append({"dispositivo_id": dispositivo.id, **dados})
        dispositivo.ultimo_seq = dados["seq"]
        self.historico(dispositivo.id).adicionar(dados["corrente_rms_a"])

    def gravar_status(self, dispositivo: Dispositivo, ts_epoch: int | None, agora_epoch: int) -> None:
        dispositivo.ultimo_status_epoch = ts_epoch if ts_epoch is not None else agora_epoch

    def alerta_aberto(self, dispositivo_id: str, tipo: str) -> AlertaAberto | None:
        for a in self.alertas:
            if a.aberto and a.dispositivo_id == dispositivo_id and a.tipo == tipo:
                return a
        return None

    def abrir_alerta(self, dispositivo_id: str, tipo: str, severidade: str, mensagem: str) -> AlertaAberto:
        a = AlertaAberto(self._proximo_id, dispositivo_id, tipo, severidade, mensagem)
        self._proximo_id += 1
        self.alertas.append(a)
        return a

    def fechar_alerta(self, dispositivo_id: str, tipo: str) -> None:
        a = self.alerta_aberto(dispositivo_id, tipo)
        if a:
            a.aberto = False

    # ---------- Leitura para painel e app ----------
    def dispositivo_existe(self, dispositivo_id: str) -> bool:
        return any(d.id == dispositivo_id for d in self.dispositivos.values())

    def listar_alertas(self, dispositivo_id: str, somente_abertos: bool = True) -> list[dict]:
        return [
            {"id": a.id, "tipo": a.tipo, "severidade": a.severidade,
             "mensagem": a.mensagem, "aberto": a.aberto}
            for a in reversed(self.alertas)
            if a.dispositivo_id == dispositivo_id and (a.aberto or not somente_abertos)
        ]

    def listar_telemetria(self, dispositivo_id: str, limite: int = 100) -> list[dict]:
        leituras = [t for t in self.telemetrias if t["dispositivo_id"] == dispositivo_id]
        return [
            {k: v for k, v in t.items() if k != "dispositivo_id"}
            for t in reversed(leituras[-limite:])
        ]

    # ---------- Usuários, vínculos e sessões ----------
    def criar_usuario(self, email: str, senha_hash: str, perfil: str) -> int:
        uid = self._proximo_usuario
        self._proximo_usuario += 1
        self.usuarios[uid] = {"id": uid, "email": email.lower(), "senha_hash": senha_hash,
                              "perfil": perfil, "ativo": True}
        return uid

    def usuario_por_email(self, email: str) -> dict | None:
        for u in self.usuarios.values():
            if u["email"] == email.lower():
                return dict(u)
        return None

    def vincular_usuario_condominio(self, usuario_id: int, condominio_id: str) -> None:
        self.usuario_condominios.add((usuario_id, condominio_id))

    def condominios_do_usuario(self, usuario_id: int) -> set[str]:
        return {c for (u, c) in self.usuario_condominios if u == usuario_id}

    def criar_sessao(self, usuario_id: int, token_hash: str, expira_epoch: float) -> None:
        self.sessoes[token_hash] = (usuario_id, expira_epoch)

    def usuario_por_sessao(self, token_hash: str, agora_epoch: float) -> dict | None:
        sessao = self.sessoes.get(token_hash)
        if sessao is None:
            return None
        usuario_id, expira = sessao
        u = self.usuarios.get(usuario_id)
        if expira <= agora_epoch or u is None or not u["ativo"]:
            return None
        return {"id": u["id"], "perfil": u["perfil"]}

    def condominio_do_dispositivo(self, dispositivo_id: str) -> str | None:
        for d in self.dispositivos.values():
            if d.id == dispositivo_id:
                return d.condominio_id
        return None
