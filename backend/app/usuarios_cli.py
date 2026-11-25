"""Cria usuários do painel e do app.

Uso (com DATABASE_URL apontando para o banco certo, definida só no seu terminal):

    python -m app.usuarios_cli criar EMAIL administrador
    python -m app.usuarios_cli criar EMAIL zelador CONDOMINIO_ID [CONDOMINIO_ID ...]

A senha é pedida no terminal, sem eco. Nunca passe a senha como argumento.
"""

import getpass
import os
import sys

from .repositorio_postgres import RepositorioPostgres
from .seguranca import hash_senha

PERFIS = ("administrador", "zelador")


def main(argv: list[str]) -> int:
    if len(argv) < 4 or argv[1] != "criar":
        print(__doc__)
        return 2

    _, _, email, perfil, *condominios = argv
    if perfil not in PERFIS:
        print(f"Perfil inválido: use {' ou '.join(PERFIS)}.")
        return 2
    if perfil == "zelador" and not condominios:
        print("Zelador precisa de pelo menos um CONDOMINIO_ID.")
        return 2

    url = os.environ.get("DATABASE_URL")
    if not url:
        print("Defina DATABASE_URL antes de rodar.")
        return 2

    senha = getpass.getpass("Senha: ")
    if len(senha) < 10:
        print("A senha precisa ter pelo menos 10 caracteres.")
        return 2
    if senha != getpass.getpass("Repita a senha: "):
        print("As senhas não conferem.")
        return 2

    repo = RepositorioPostgres(url)
    if repo.usuario_por_email(email) is not None:
        print("Já existe usuário com esse e-mail.")
        return 1

    uid = repo.criar_usuario(email, hash_senha(senha), perfil)
    for condominio in condominios:
        repo.vincular_usuario_condominio(uid, condominio)
    print(f"Usuário criado: {email} ({perfil}), id {uid}.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
