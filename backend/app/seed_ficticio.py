"""Dados FICTÍCIOS para desenvolvimento e testes.

TUDO neste arquivo é fictício. Nada aqui corresponde ao condomínio real.
Substituir pelos dados reais do cadastro (Fase 3) quando forem conhecidos:
- identificadores, nomes e endereços;
- modelo, corrente nominal e fases das bombas;
- tokens de dispositivo, que nunca devem ser versionados em código.
"""

from .repositorio import Dispositivo, RepositorioMemoria, hash_token

# FICTÍCIO: token de teste. Não usar em produção.
TOKEN_FICTICIO = "TOKEN-FICTICIO-NAO-USAR-EM-PRODUCAO"


def carregar_dados_ficticios(repo: RepositorioMemoria) -> RepositorioMemoria:
    # FICTÍCIO: condomínio, casa de máquinas e bomba inventados
    repo.cadastrar(Dispositivo(
        id="dispositivo-ficticio-001",
        condominio_id="condominio-ficticio-alfa",   # FICTÍCIO
        casa_id="casa-ficticia-01",                  # FICTÍCIO
        bomba_id="bomba-ficticia-01",                # FICTÍCIO
        token_hash=hash_token(TOKEN_FICTICIO),
    ))
    return repo
