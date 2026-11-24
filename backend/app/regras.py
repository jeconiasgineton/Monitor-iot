"""Regras de alerta do piloto.

Os limiares abaixo são FICTÍCIOS. Devem ser substituídos pelos valores
calibrados no local (Fase 1 e Fase 6). Ver backend/README.md.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Limites:
    # FICTÍCIO: corrente abaixo deste valor com bomba ligada indica bomba em seco.
    corrente_seca_a: float = 2.0
    # FICTÍCIO: corrente acima deste valor indica sobrecarga.
    corrente_sobrecarga_a: float = 16.0
    # FICTÍCIO: quantas leituras seguidas abaixo do limite antes de alertar.
    leituras_confirmacao: int = 2
    # FICTÍCIO: segundos sem heartbeat para considerar o dispositivo offline.
    offline_s: int = 300


@dataclass
class Alerta:
    tipo: str
    severidade: str
    mensagem: str


@dataclass
class Historico:
    """Últimas leituras de corrente RMS de uma bomba, em ordem de chegada."""
    valores: list[float] = field(default_factory=list)
    tamanho: int = 10

    def adicionar(self, valor: float) -> None:
        self.valores.append(valor)
        if len(self.valores) > self.tamanho:
            self.valores.pop(0)


def avaliar_telemetria(corrente_rms_a: float, historico: Historico, limites: Limites) -> list[Alerta]:
    """Avalia uma leitura nova. O histórico deve já conter a leitura atual."""
    alertas: list[Alerta] = []
    n = limites.leituras_confirmacao
    recentes = historico.valores[-n:]

    if len(recentes) == n and all(v < limites.corrente_seca_a for v in recentes):
        alertas.append(Alerta(
            tipo="bomba_em_seco",
            severidade="critica",
            mensagem=f"Corrente abaixo de {limites.corrente_seca_a} A por {n} leituras seguidas.",
        ))

    if corrente_rms_a > limites.corrente_sobrecarga_a:
        alertas.append(Alerta(
            tipo="sobrecarga",
            severidade="critica",
            mensagem=f"Corrente de {corrente_rms_a:.2f} A acima de {limites.corrente_sobrecarga_a} A.",
        ))

    return alertas


def avaliar_offline(ultimo_status_epoch: int | None, agora_epoch: int, limites: Limites) -> Alerta | None:
    """Gera alerta se o último heartbeat for antigo demais."""
    if ultimo_status_epoch is None:
        return Alerta(tipo="sem_heartbeat", severidade="atencao",
                      mensagem="Dispositivo nunca enviou heartbeat.")
    if agora_epoch - ultimo_status_epoch > limites.offline_s:
        return Alerta(tipo="offline", severidade="atencao",
                      mensagem=f"Sem heartbeat há mais de {limites.offline_s} s.")
    return None
