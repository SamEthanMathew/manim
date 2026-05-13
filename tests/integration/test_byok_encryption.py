"""BYOK roundtrip — key encrypted by Vercel API, decrypted by Modal worker."""
from __future__ import annotations

from workers.lib.byok import decrypt, encrypt


def test_encrypt_decrypt_roundtrip():
    key = "test-server-secret-do-not-use-in-prod"
    plaintext = "sk-proj-abcdef1234567890"
    cipher = encrypt(key, plaintext)
    assert isinstance(cipher, bytes)
    assert cipher != plaintext.encode()
    assert decrypt(key, cipher) == plaintext


def test_wrong_key_fails():
    cipher = encrypt("key-a", "secret")
    try:
        decrypt("key-b", cipher)
    except Exception:
        return  # expected
    assert False, "Wrong key should not decrypt"
