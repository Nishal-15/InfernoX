# InfernoX Security Architecture

## Password Storage — Argon2id

Passwords are hashed using **Argon2id** (memory-hard), never stored in plaintext.

```python
from argon2 import PasswordHasher
ph = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=2)
hashed = ph.hash(plain_password)
ph.verify(hashed, plain_password)  # raises VerifyMismatchError on failure
```

> Argon2id is the OWASP-recommended algorithm for 2024+, winning the Password Hashing Competition.

## JWT Session Management

- **Algorithm**: HS256 with a 256-bit secret (`SECRET_KEY`)
- **Expiry**: Default 60 minutes, configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`
- **Sub claim**: Always a string (user ID stringified)
- Token is delivered to clients and stored in `localStorage` under `infernox_token`

### JWT Payload Structure
```json
{
  "sub": "42",
  "email": "user@example.com",
  "is_superadmin": false,
  "exp": 1234567890,
  "iat": 1234564290
}
```

## Webhook Signing — HMAC-SHA256

All outbound webhook deliveries include a signature header:
```
X-InfernoX-Signature: sha256=<hex_digest>
```

Generated as:
```python
import hmac, hashlib
sig = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
```

Recipients should validate with `hmac.compare_digest` to prevent timing attacks.

## Payment Webhook Integrity — Razorpay Signature

Razorpay payment callbacks are verified with HMAC-SHA256:
```python
import hmac, hashlib
expected = hmac.new(
    razorpay_secret.encode(),
    f"{order_id}|{payment_id}".encode(),
    hashlib.sha256
).hexdigest()
assert hmac.compare_digest(expected, provided_signature)
```

## API Key Security

- Keys follow the format `inf_live_<8char_prefix>.<32char_secret>`
- Only `key_prefix` and `SHA-256(secret)` are stored in the database
- The raw key is returned exactly once at creation time and cannot be retrieved again
- Keys can be revoked by setting `revoked_at` (soft delete)

## Cross-Tenant Isolation

1. **Server-side only**: `organization_id` is never trusted from the client request body
2. The `X-Organization-Id` header specifies intent; actual membership is validated from JWT
3. Cross-tenant access attempts return `403 FORBIDDEN`
4. Superadmins bypass tenant isolation for platform management

## Audit Logging

All security events write to `platform_audit_logs`:
- `USER_LOGIN` / `USER_LOGOUT`
- `ROLE_CHANGED`
- `MEMBER_INVITED` / `MEMBER_REMOVED`
- `API_KEY_CREATED` / `API_KEY_REVOKED`
- `SUBSCRIPTION_CHANGED`

Audit logs are **append-only** (no update/delete endpoints).
