"""Utilitários de banco: aplicar esquema e carregar dados FICTÍCIOS.

Uso (a URL vem da variável DATABASE_URL):
  python -m app.banco schema      # aplica sql/schema.sql
  python -m app.banco timescale   # aplica sql/timescale.sql (requer TimescaleDB)
  python -m app.banco seed        # carrega dados FICTÍCIOS de app/seed_ficticio.py
"""

import os
import sys
from pathlib import Path

import psycopg

from .repositorio_postgres import RepositorioPostgres
from .seed_ficticio import carregar_dados_ficticios
from .repositorio import RepositorioMemoria

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


def _url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("Defina DATABASE_URL com a conexão do Neon ou do banco local.")
    return url


def aplicar_sql(arquivo: str) -> None:
    sql = (SQL_DIR / arquivo).read_text(encoding="utf-8")
    with psycopg.connect(_url(), autocommit=True) as con:
        con.execute(sql)
    print(f"Aplicado: {arquivo}")


def semear_ficticio() -> None:
    # Carrega o seed em memória para obter os dispositivos e grava no banco.
    origem = carregar_dados_ficticios(RepositorioMemoria())
    destino = RepositorioPostgres(_url())
    for dispositivo in origem.dispositivos.values():
        destino.cadastrar(dispositivo)
    print(f"Dados fictícios carregados: {len(origem.dispositivos)} dispositivo(s).")


if __name__ == "__main__":
    comando = sys.argv[1] if len(sys.argv) > 1 else ""
    if comando == "schema":
        aplicar_sql("schema.sql")
    elif comando == "timescale":
        aplicar_sql("timescale.sql")
    elif comando == "seed":
        semear_ficticio()
    else:
        sys.exit(__doc__)
