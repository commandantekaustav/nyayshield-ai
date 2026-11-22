"""Zstandard (level 3) + ChaCha20-Poly1305 authenticated encryption for research logs.

Key material is read exclusively from the ``IDEA_ENC_KEY`` environment variable
(URL-safe base64-encoded 32-byte key) or passed explicitly by callers/tests.
Never hardcode or commit keys.
"""

from __future__ import annotations

import base64
import json
import os
import zlib
from pathlib import Path
from typing import Any

try:
    import zstandard as zstd
except ImportError:  # pragma: no cover - fallback only if zstandard is missing
    zstd = None  # type: ignore[assignment]

try:
    from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
except ImportError:  # pragma: no cover
    ChaCha20Poly1305 = None  # type: ignore[assignment]

MAGIC_ZSTD = b"ZCP1"  # ZSTD (level 3) + ChaCha20-Poly1305 v1
NONCE_SIZE = 12
ZSTD_LEVEL = 3


def generate_key() -> str:
    """Return a freshly generated URL-safe base64 32-byte key for IDEA_ENC_KEY."""
    return base64.urlsafe_b64encode(os.urandom(32)).decode("ascii")


def load_dotenv_if_present(env_paths: tuple[Path, ...] | None = None) -> dict[str, str]:
    """Load KEY=VALUE pairs from repo-root or research `.env` without overriding os.environ."""
    loaded: dict[str, str] = {}
    if env_paths is None:
        repo_root = Path(__file__).resolve().parents[3]
        env_paths = (repo_root / ".env", repo_root / "research" / ".env")

    for path in env_paths:
        if not path.is_file():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key_name, val = line.split("=", 1)
            key_name = key_name.strip()
            val = val.strip().strip('"').strip("'")
            if key_name and key_name not in os.environ and val:
                os.environ[key_name] = val
                loaded[key_name] = val
    return loaded


def _resolve_key(key: bytes | str | None = None) -> bytes:
    if key is None:
        load_dotenv_if_present()
    raw_key = key if key is not None else os.getenv("IDEA_ENC_KEY")
    if not raw_key:
        raise ValueError(
            "IDEA_ENC_KEY environment variable is not set. "
            "Generate one with encrypt_util.generate_key() and export IDEA_ENC_KEY."
        )
    if isinstance(raw_key, str):
        decoded = base64.urlsafe_b64decode(raw_key.encode("ascii"))
    else:
        decoded = raw_key
    if len(decoded) != 32:
        raise ValueError(f"IDEA_ENC_KEY must decode to exactly 32 bytes (got {len(decoded)}).")
    return decoded


def compress_encrypt(data: dict[str, Any], key: bytes | str | None = None) -> bytes:
    """Serialize ``data`` to JSON, compress with ZSTD level 3, and encrypt via ChaCha20-Poly1305."""
    if ChaCha20Poly1305 is None:
        raise RuntimeError(
            "The 'cryptography' package is required for ChaCha20-Poly1305 encryption. "
            "Install dependencies via: pip install -r research/requirements.txt"
        )
    key_bytes = _resolve_key(key)
    raw = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    if zstd is not None:
        comp = zstd.ZstdCompressor(level=ZSTD_LEVEL).compress(raw)
        header = MAGIC_ZSTD
    else:  # pragma: no cover - zlib fallback when zstandard wheel isn't present
        comp = zlib.compress(raw, level=6)
        header = b"ZLB1"

    nonce = os.urandom(NONCE_SIZE)
    aead = ChaCha20Poly1305(key_bytes)
    ciphertext = aead.encrypt(nonce, comp, header)
    return header + nonce + ciphertext


def decrypt_decompress(blob: bytes, key: bytes | str | None = None) -> dict[str, Any]:
    """Verify ChaCha20-Poly1305 tag, decrypt, decompress ZSTD payload, and parse JSON."""
    if ChaCha20Poly1305 is None:
        raise RuntimeError(
            "The 'cryptography' package is required for ChaCha20-Poly1305 decryption."
        )
    if len(blob) < 4 + NONCE_SIZE + 16:
        raise ValueError("Encrypted blob is truncated or malformed.")

    key_bytes = _resolve_key(key)
    header = blob[:4]
    nonce = blob[4 : 4 + NONCE_SIZE]
    ciphertext = blob[4 + NONCE_SIZE :]

    aead = ChaCha20Poly1305(key_bytes)
    comp = aead.decrypt(nonce, ciphertext, header)

    if header == MAGIC_ZSTD:
        if zstd is None:
            raise RuntimeError("Blob uses Zstandard compression, but 'zstandard' is not installed.")
        raw = zstd.ZstdDecompressor().decompress(comp)
    elif header == b"ZLB1":  # pragma: no cover
        raw = zlib.decompress(comp)
    else:
        raise ValueError(f"Unsupported encryption header: {header!r}")

    return json.loads(raw.decode("utf-8"))
