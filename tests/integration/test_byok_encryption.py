"""BYOK roundtrip — key encrypted by Vercel API, decrypted by Modal worker."""
from __future__ import annotations

import pytest

from workers.lib.byok import decrypt, encrypt
from workers.lib.errors import PipelineError


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


# ─── Key rotation ─────────────────────────────────────────────────────────────


def test_new_key_works_for_new_data_old_ciphertext_fails():
    """After rotating the server key:
       - data encrypted with the new key roundtrips successfully
       - existing ciphertext encrypted under the old key fails to decrypt
    """
    old_key = "rotation-old"
    new_key = "rotation-new"

    old_cipher = encrypt(old_key, "legacy-secret")

    # New cipher under the new key roundtrips.
    new_cipher = encrypt(new_key, "fresh-secret")
    assert decrypt(new_key, new_cipher) == "fresh-secret"

    # Old ciphertext under the old key still works (sanity).
    assert decrypt(old_key, old_cipher) == "legacy-secret"

    # Old ciphertext under the new key MUST fail.
    with pytest.raises(PipelineError):
        decrypt(new_key, old_cipher)


def test_rotated_key_does_not_decrypt_other_users_data():
    """Two independent users with their own keys must never see each other's
    plaintext when the server-side key is rotated.
    """
    user_a_key = "user-a-server-key"
    user_b_key = "user-b-server-key"
    ct_a = encrypt(user_a_key, "sk-proj-A")
    ct_b = encrypt(user_b_key, "sk-proj-B")

    assert decrypt(user_a_key, ct_a) == "sk-proj-A"
    assert decrypt(user_b_key, ct_b) == "sk-proj-B"

    with pytest.raises(PipelineError):
        decrypt(user_a_key, ct_b)
    with pytest.raises(PipelineError):
        decrypt(user_b_key, ct_a)


# ─── Boundary sizes ───────────────────────────────────────────────────────────


def test_encrypt_single_character_roundtrip():
    key = "size-test"
    cipher = encrypt(key, "x")
    assert decrypt(key, cipher) == "x"


def test_encrypt_empty_string_roundtrip():
    """Empty plaintext is a valid edge case; Fernet should still handle it."""
    key = "size-test"
    cipher = encrypt(key, "")
    assert decrypt(key, cipher) == ""


def test_encrypt_100kb_plaintext_roundtrip():
    key = "size-test"
    big = "A" * 100_000
    cipher = encrypt(key, big)
    out = decrypt(key, cipher)
    assert out == big
    assert len(out) == 100_000


def test_encrypt_unicode_plaintext_roundtrip():
    key = "unicode-test"
    plaintext = "sk-test-あいう-\U0001F511-end"
    cipher = encrypt(key, plaintext)
    assert decrypt(key, cipher) == plaintext


# ─── Non-determinism (random IV) ─────────────────────────────────────────────


def test_two_encrypts_of_same_plaintext_differ():
    """Fernet uses a random 128-bit IV per token; identical inputs must
    produce different ciphertexts. If this ever fails we have a serious
    cryptographic regression.
    """
    key = "iv-test"
    plaintext = "sk-proj-same-input"
    a = encrypt(key, plaintext)
    b = encrypt(key, plaintext)
    assert a != b, "Ciphertexts must differ — random IV broken"
    # Both still decrypt to the same plaintext.
    assert decrypt(key, a) == plaintext
    assert decrypt(key, b) == plaintext


def test_corrupted_ciphertext_fails():
    """Mutating a single byte of the ciphertext must fail decryption."""
    key = "tamper-test"
    cipher = bytearray(encrypt(key, "secret"))
    # Flip a byte near the end (HMAC region) so the integrity check trips.
    cipher[-1] ^= 0x01
    with pytest.raises(PipelineError):
        decrypt(key, bytes(cipher))
