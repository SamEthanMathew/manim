/**
 * BYOK encryption — Node-side Fernet-equivalent using AES-256-GCM.
 *
 * Keys are encrypted server-side before being written to user_settings.
 * Decryption happens only inside Modal workers (see modal/lib/byok.py).
 *
 * Cipher format (base64): [12-byte iv][16-byte tag][ciphertext]
 */
import { createCipheriv, createDecipheriv, createHash, randomBytes } from "node:crypto";

const ALG = "aes-256-gcm";
const IV_LEN = 12;

function deriveKey(serverKey: string): Buffer {
  return createHash("sha256").update(serverKey, "utf8").digest();
}

export function encryptByok(serverKey: string, plaintext: string): Buffer {
  const key = deriveKey(serverKey);
  const iv = randomBytes(IV_LEN);
  const cipher = createCipheriv(ALG, key, iv);
  const enc = Buffer.concat([cipher.update(plaintext, "utf8"), cipher.final()]);
  const tag = cipher.getAuthTag();
  return Buffer.concat([iv, tag, enc]);
}

export function decryptByok(serverKey: string, ciphertext: Buffer): string {
  const key = deriveKey(serverKey);
  const iv = ciphertext.subarray(0, IV_LEN);
  const tag = ciphertext.subarray(IV_LEN, IV_LEN + 16);
  const enc = ciphertext.subarray(IV_LEN + 16);
  const decipher = createDecipheriv(ALG, key, iv);
  decipher.setAuthTag(tag);
  return Buffer.concat([decipher.update(enc), decipher.final()]).toString("utf8");
}
