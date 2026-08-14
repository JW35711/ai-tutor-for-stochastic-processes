"""Small, dependency-free authentication primitives for the interview demo."""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
from typing import Final


USERNAME_RE: Final = re.compile(r"^[a-z0-9_]{3,32}$")
PASSWORD_MIN_LENGTH: Final = 8
PASSWORD_MAX_LENGTH: Final = 128
_SCRYPT_N: Final = 2**14
_SCRYPT_R: Final = 8
_SCRYPT_P: Final = 1
_SCRYPT_DKLEN: Final = 32


def normalize_username(value: object) -> str:
    """Return a bounded, case-insensitive username or raise a safe error."""

    if not isinstance(value, str):
        raise ValueError("username must be a string")
    username = value.strip().lower()
    if not USERNAME_RE.fullmatch(username):
        raise ValueError("username must use 3-32 letters, numbers, or underscores")
    return username


def validate_password(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("password must be a string")
    if not PASSWORD_MIN_LENGTH <= len(value) <= PASSWORD_MAX_LENGTH:
        raise ValueError("password must be 8-128 characters")
    if any(ord(char) < 32 for char in value):
        raise ValueError("password contains invalid control characters")
    return value


def hash_password(password: str) -> str:
    """Hash with salted scrypt and a versioned, self-describing format."""

    password = validate_password(password)
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_SCRYPT_DKLEN,
    )
    encoder = base64.urlsafe_b64encode
    return "scrypt$v1${}${}${}${}${}".format(
        _SCRYPT_N,
        _SCRYPT_R,
        _SCRYPT_P,
        encoder(salt).decode("ascii").rstrip("="),
        encoder(digest).decode("ascii").rstrip("="),
    )


def verify_password(password: object, encoded: object) -> bool:
    """Verify without revealing whether the username or password was wrong."""

    if not isinstance(password, str) or not isinstance(encoded, str):
        return False
    try:
        scheme, version, raw_n, raw_r, raw_p, raw_salt, raw_digest = encoded.split("$")
        if scheme != "scrypt" or version != "v1":
            return False
        n, r, p = int(raw_n), int(raw_r), int(raw_p)
        if (n, r, p) != (_SCRYPT_N, _SCRYPT_R, _SCRYPT_P):
            return False
        salt = base64.urlsafe_b64decode(raw_salt + "===")
        expected = base64.urlsafe_b64decode(raw_digest + "===")
        actual = hashlib.scrypt(
            password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=len(expected)
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
