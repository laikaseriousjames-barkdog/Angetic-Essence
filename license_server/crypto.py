"""Server-side cryptographic operations — key generation & license signing."""

import os
import base64
from pathlib import Path

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.backends import default_backend

    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


KEY_DIR = Path(__file__).resolve().parent / "keys"
PRIVATE_KEY_PATH = KEY_DIR / "private.pem"
PUBLIC_KEY_PATH = KEY_DIR / "public.pem"


def _ensure_key_dir():
    KEY_DIR.mkdir(exist_ok=True)


def generate_key_pair(force: bool = False):
    _ensure_key_dir()
    if PRIVATE_KEY_PATH.exists() and not force:
        return

    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )

    PRIVATE_KEY_PATH.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )

    public_key = private_key.public_key()
    PUBLIC_KEY_PATH.write_bytes(
        public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )


def load_private_key():
    if not HAS_CRYPTO:
        return None
    if not PRIVATE_KEY_PATH.exists():
        generate_key_pair()
    try:
        return serialization.load_pem_private_key(
            PRIVATE_KEY_PATH.read_bytes(),
            password=None,
            backend=default_backend(),
        )
    except Exception:
        return None


def load_public_key():
    if not HAS_CRYPTO:
        return None
    if not PUBLIC_KEY_PATH.exists():
        generate_key_pair()
    try:
        return serialization.load_pem_public_key(
            PUBLIC_KEY_PATH.read_bytes(), backend=default_backend()
        )
    except Exception:
        return None


def sign_license(user_id: str) -> str | None:
    private_key = load_private_key()
    if private_key is None:
        return None
    try:
        signature = private_key.sign(
            user_id.encode(),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        combined = f"{user_id}:{base64.b64encode(signature).decode()}"
        return base64.b64encode(combined.encode()).decode()
    except Exception:
        return None


def verify_license(license_key: str) -> bool:
    if not license_key or not HAS_CRYPTO:
        return False
    try:
        decoded = base64.b64decode(license_key.encode()).decode()
        user_id, signature_b64 = decoded.rsplit(":", 1)
        signature = base64.b64decode(signature_b64.encode())
        public_key = load_public_key()
        if public_key is None:
            return False
        public_key.verify(
            signature, user_id.encode(), padding.PKCS1v15(), hashes.SHA256()
        )
        return True
    except Exception:
        return False
