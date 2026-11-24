"""Modelos de entrada conforme docs/contrato-mensagens.md (versão 0.2)."""

from pydantic import BaseModel, Field


class TelemetriaIn(BaseModel):
    v: int = Field(1, ge=1)
    ts: int | None = None
    seq: int = Field(..., ge=0)
    corrente_rms_a: float = Field(..., ge=0)
    corrente_max_a: float = Field(..., ge=0)
    corrente_min_a: float = Field(..., ge=0)
    amostras: int = Field(..., ge=1)
    rssi_dbm: int | None = None
    fw: str = Field(..., min_length=1, max_length=20)


class StatusIn(BaseModel):
    v: int = Field(1, ge=1)
    ts: int | None = None
    uptime_s: int = Field(..., ge=0)
    rssi_dbm: int | None = None
    pendentes: int = Field(0, ge=0)
    fw: str = Field(..., min_length=1, max_length=20)
