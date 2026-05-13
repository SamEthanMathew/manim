"""BYOK key encryption / decryption.

We use Fernet (AES-128-CBC + HMAC) over a server-side key. Lighter than building
on top of pgcrypto and equally suitable for short secrets.

Stored ciphertext format in DB: raw Fernet token bytes. The DB column is bytea.
"""
from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from workers.lib.errors import PipelineError


def _make_fernet(server_key: str) -> Fernet:
    """Derive a 32-byte url-safe-b64 key from the server secret."""
    digest = hashlib.sha256(server_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(server_key: str, plaintext: str) -> bytes:
    return _make_fernet(server_key).encrypt(plaintext.encode("utf-8"))


def decrypt(server_key: str, ciphertext: bytes | str) -> str:
    """Decrypt a Fernet token.

    Accepts either raw bytes (direct psycopg path) or a Postgres hex bytea
    representation as a string (`\\x` prefix, what supabase-py returns from
    PostgREST). Auto-detects format.
    """
    if isinstance(ciphertext, str):
        if ciphertext.startswith("\\x"):
            # Postgres bytea hex format: '\xabcd...' -> bytes
            ciphertext = bytes.fromhex(ciphertext[2:])
        else:
            # Defensive: maybe it's already the Fernet token base64
            ciphertext = ciphertext.encode("utf-8")
    elif isinstance(ciphertext, memoryview):
        ciphertext = bytes(ciphertext)

    try:
        return _make_fernet(server_key).decrypt(ciphertext).decode("utf-8")
    except InvalidToken as e:
        raise PipelineError(
            "BYOK decryption failed — likely wrong server key or corrupted ciphertext",
        ) from e
