import hmac
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError
from app.core.config import settings

# Initialize Argon2id password hasher (RFC 9106 recommended parameters)
_hasher = PasswordHasher(
    time_cost=2,
    memory_cost=65536,  # 64 MB
    parallelism=2,
    hash_len=32,
    salt_len=16
)


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using Argon2id.
    """
    return _hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against an Argon2id hash.
    Safely handles invalid formats and mismatches.
    """
    try:
        return _hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, InvalidHashError):
        return False
    except Exception:
        return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a signed JWT access token.
    """
    to_encode = data.copy()
    if "sub" in to_encode and to_encode["sub"] is not None:
        to_encode["sub"] = str(to_encode["sub"])
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "iss": "infernox-platform"
    })
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate a JWT access token.
    Returns payload dictionary or None if invalid or expired.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            issuer="infernox-platform"
        )
        return payload
    except jwt.PyJWTError:
        return None


def generate_api_key(name: str = "default") -> Tuple[str, str, str]:
    """
    Generate a high-entropy API key.
    Returns: (raw_key, prefix, hashed_secret)
    Format: inf_live_<short_prefix>_<high_entropy_secret>
    Only the prefix and hashed_secret are stored in the database.
    """
    short_prefix = secrets.token_hex(4)
    secret_part = secrets.token_urlsafe(32)
    raw_key = f"inf_live_{short_prefix}_{secret_part}"
    prefix = f"inf_{short_prefix}"
    hashed_secret = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    return raw_key, prefix, hashed_secret


def hash_api_key(raw_key: str) -> str:
    """
    Computes SHA-256 hash of an API key for comparison against database.
    """
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def hash_api_key_secret(secret: str) -> str:
    """
    Computes SHA-256 hash of an API key or secret.
    """
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def generate_webhook_secret() -> str:
    """
    Generates a secure random secret key for an outbound webhook endpoint.
    """
    return secrets.token_hex(24)


def generate_webhook_signature(payload_bytes: bytes, secret: str) -> str:
    """
    Computes standard HMAC-SHA256 signature for webhook payload.
    """
    return hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()


def compute_webhook_signature(secret: str, payload_bytes: bytes, timestamp: str) -> str:
    """
    Computes HMAC-SHA256 signature for webhook payload:
    signature = HMAC_SHA256(secret, f"{timestamp}.{payload_str}")
    """
    message = f"{timestamp}.".encode("utf-8") + payload_bytes
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def verify_webhook_signature(secret: str, payload_bytes: bytes, timestamp: str, signature: str) -> bool:
    """
    Constant-time comparison of webhook signature against expected HMAC-SHA256.
    """
    expected = compute_webhook_signature(secret, payload_bytes, timestamp)
    return hmac.compare_digest(expected, signature)


def generate_invitation_token() -> str:
    """
    Generate an unguessable single-use invitation token.
    """
    return secrets.token_urlsafe(32)

