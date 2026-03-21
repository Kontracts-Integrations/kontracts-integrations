import json
import logging

from cryptography.fernet import Fernet

from app.config import settings

logger = logging.getLogger(__name__)

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        if not settings.fernet_key:
            # Generate a temporary key (not persistent — warn loudly)
            logger.warning(
                "FERNET_KEY not configured. Generating temporary key. "
                "Credentials stored with this key will not survive restarts."
            )
            key = Fernet.generate_key()
        else:
            key = settings.fernet_key.encode()
        _fernet = Fernet(key)
    return _fernet


def encrypt_credentials(credentials: dict) -> str:
    f = _get_fernet()
    plaintext = json.dumps(credentials).encode()
    return f.encrypt(plaintext).decode()


def decrypt_credentials(encrypted: str) -> dict:
    f = _get_fernet()
    decrypted = f.decrypt(encrypted.encode())
    return json.loads(decrypted)
