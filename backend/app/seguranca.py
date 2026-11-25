"""Senhas e sessões de usuário. Usa apenas a biblioteca padrão (scrypt e secrets)."""

import hashlib
import hmac
import secrets

_N, _R, _P, _DKLEN = 2**14, 8, 1, 32


def hash_senha(senha: str) -> str:
    sal = secrets.token_bytes(16)
    chave = hashlib.scrypt(senha.encode("utf-8"), salt=sal, n=_N, r=_R, p=_P, dklen=_DKLEN)
    return f"scrypt${sal.hex()}${chave.hex()}"


def verificar_senha(senha: str, armazenado: str) -> bool:
    try:
        _, sal_hex, chave_hex = armazenado.split("$")
    except ValueError:
        return False
    chave = hashlib.scrypt(
        senha.encode("utf-8"), salt=bytes.fromhex(sal_hex), n=_N, r=_R, p=_P, dklen=_DKLEN
    )
    return hmac.compare_digest(chave, bytes.fromhex(chave_hex))


def novo_token() -> str:
    # token_urlsafe usa só caracteres ASCII, então é seguro em cabeçalho HTTP.
    return secrets.token_urlsafe(32)
