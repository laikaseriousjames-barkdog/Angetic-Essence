"""License validation — cryptographic RSA verification + async HTTP validation."""

import os
import sys
import json
import base64
import asyncio
from pathlib import Path

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.backends import default_backend

    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


_PUBLIC_KEY_PEM = (
    "-----BEGIN PUBLIC KEY-----\n"
    "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAx5KqE3GAVySJfHqFh1dM\n"
    "vFnKz3pVo7Y5L2JNXhPqJmHLaOGKIPJhGmYt6gS2uQKfFVj7bZ0XGQHx3YTqGiJ7\n"
    "cWvLPn12dRlLzkO0yQlOq+XgQ3R3rY5KJmN1o0s/WfB2hGeX9LpOym8XJx1kL6yB\n"
    "9TgSXoOhmWCRFuXErYa8T3BkK80hnSQPCDLjpjYULNqqU3rKo4Y/5r0FU35QkFGw\n"
    "CJNHLo2f3hVLGjjL6gRF7ysarY4cYbCnT/wLHqFB8CJ5FrR6vUG9xHLPZmF7u5j0\n"
    "HWiEQWpLwf8GqKG/wPR+RKQazffG+2nGRFWMWrLiB12t5FYwQ7YIjYgS1dxYCqDE\n"
    "mQIDAQAB\n"
    "-----END PUBLIC KEY-----\n"
)


def _load_public_key():
    if not HAS_CRYPTO:
        return None
    try:
        return serialization.load_pem_public_key(
            _PUBLIC_KEY_PEM.encode(), backend=default_backend()
        )
    except Exception:
        return None


def generate_key_pair() -> tuple:
    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )
    public_key = private_key.public_key()
    return private_key, public_key


def sign_license(user_id: str, private_key) -> str:
    signature = private_key.sign(
        user_id.encode(),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    combined = f"{user_id}:{base64.b64encode(signature).decode()}"
    return base64.b64encode(combined.encode()).decode()


def verify_license(license_key: str) -> bool:
    if not license_key or not HAS_CRYPTO:
        return False
    try:
        decoded = base64.b64decode(license_key.encode()).decode()
        user_id, signature_b64 = decoded.rsplit(":", 1)
        signature = base64.b64decode(signature_b64.encode())
        public_key = _load_public_key()
        if public_key is None:
            return False
        public_key.verify(
            signature, user_id.encode(), padding.PKCS1v15(), hashes.SHA256()
        )
        return True
    except Exception:
        return False


def _get_validation_url() -> str:
    config_path = Path(__file__).resolve().parent.parent / "config.yaml"
    if config_path.exists():
        try:
            import yaml

            cfg = yaml.safe_load(config_path.read_text()) or {}
            url = (cfg.get("license") or {}).get("validation_url", "")
            if url:
                return url
        except Exception:
            pass
    return "https://api.angeticessence.com/validate"


async def async_validate(license_key: str) -> bool:
    url = _get_validation_url()
    try:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json={"license_key": license_key},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("valid", False)
                return False
    except ImportError:
        try:
            import urllib.request
            import urllib.error

            payload = json.dumps({"license_key": license_key}).encode()
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                return data.get("valid", False)
        except Exception:
            return False
    except Exception:
        return False


def validate_or_exit():
    if os.environ.get("AE_DEV_MODE") == "true":
        print("[DEV MODE] Bypassing license validation.")
        return
    config_path = Path(__file__).resolve().parent.parent / "config.yaml"
    license_key = ""
    if config_path.exists():
        try:
            import yaml

            cfg = yaml.safe_load(config_path.read_text()) or {}
            license_key = (cfg.get("license") or {}).get("key", "")
        except Exception:
            pass

    if not license_key:
        print("CRITICAL: No license key found in config.yaml")
        sys.exit("CRITICAL: Invalid License Key.")

    crypto_ok = verify_license(license_key)

    async def _check():
        return await async_validate(license_key)

    try:
        loop = asyncio.get_running_loop()
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(1) as pool:
            remote_ok = pool.submit(asyncio.run, _check()).result()
    except RuntimeError:
        remote_ok = asyncio.run(_check())
    except Exception:
        remote_ok = False

    if not crypto_ok:
        print("CRITICAL: Cryptographic license verification failed.")
        print("  The license key is invalid or has been tampered with.")
        sys.exit("CRITICAL: Invalid License Key.")

    if not remote_ok:
        print("WARNING: Remote license validation server unreachable.")
        print("  Proceeding with offline cryptographic validation only.")
