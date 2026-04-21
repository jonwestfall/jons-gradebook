import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet

from app.core.config import get_settings


@lru_cache
def get_fernet() -> Fernet:
    settings = get_settings()
    configured = settings.encryption_key.strip()
    if configured:
        key = configured.encode("utf-8")
    else:
        # Deterministic local fallback so development can start without manual key generation.
        digest = hashlib.sha256(settings.secret_key.encode("utf-8")).digest()
        key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_text(value: str) -> str:
    if not value:
        return ""
    token = get_fernet().encrypt(value.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_text(value: str) -> str:
    if not value:
        return ""
    decoded = get_fernet().decrypt(value.encode("utf-8"))
    return decoded.decode("utf-8")


def encrypt_bytes(value: bytes) -> bytes:
    return get_fernet().encrypt(value)


def decrypt_bytes(value: bytes) -> bytes:
    return get_fernet().decrypt(value)
