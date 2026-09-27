"""Password hashing, signed tokens and input/file validation."""

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from pathlib import Path
from typing import Optional

from config import (
    ALLOWED_UPLOAD_EXTENSIONS,
    MAX_UPLOAD_BYTES,
    PASSWORD_HASH_ITERATIONS,
    SECRET_KEY,
    TOKEN_TTL_SECONDS,
)


# ------------------------------------------------------------------ passwords
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt, PASSWORD_HASH_ITERATIONS
    )
    return f"pbkdf2_sha256${PASSWORD_HASH_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt_hex, digest_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except Exception:
        return False


# ------------------------------------------------------------------ tokens
def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _b64d(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def create_access_token(user_id: int, role: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "role": role,
        "email": email,
        "iat": int(time.time()),
        "exp": int(time.time()) + TOKEN_TTL_SECONDS,
        "jti": secrets.token_hex(8),
    }
    body = _b64e(json.dumps(payload, separators=(",", ":")).encode())
    signature = hmac.new(SECRET_KEY.encode(), body.encode(), hashlib.sha256).digest()
    return f"{body}.{_b64e(signature)}"


def decode_access_token(token: str) -> Optional[dict]:
    try:
        body, signature = token.split(".")
        expected = hmac.new(
            SECRET_KEY.encode(), body.encode(), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(_b64e(expected), signature):
            return None
        payload = json.loads(_b64d(body))
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


# ------------------------------------------------------------------ validation
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_filename(name: str) -> str:
    name = os.path.basename(name or "document")
    name = _SAFE_NAME.sub("_", name).strip("._-") or "document"
    return name[:180]


def validate_upload(filename: str, size_bytes: int) -> tuple[bool, str]:
    ext = Path(filename or "").suffix.lower()
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_UPLOAD_EXTENSIONS))
        return False, f"Unsupported file type '{ext or 'unknown'}'. Allowed: {allowed}"
    if size_bytes > MAX_UPLOAD_BYTES:
        limit_mb = MAX_UPLOAD_BYTES // (1024 * 1024)
        return False, f"File is too large. Maximum size is {limit_mb} MB."
    if size_bytes <= 0:
        return False, "The uploaded file is empty."
    return True, ""


def clean_text(value: str, max_len: int = 8000) -> str:
    if value is None:
        return ""
    value = str(value).replace("\x00", "").strip()
    return value[:max_len]
