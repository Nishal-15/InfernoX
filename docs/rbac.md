# InfernoX RBAC System

## Role Hierarchy

| Role | Code | Level | Description |
|------|------|-------|-------------|
| Super Admin | `SUPER_ADMIN` | 0 | Full platform access, cross-tenant |
| Org Admin | `ORG_ADMIN` | 1 | Full organization management |
| Analyst | `ANALYST` | 2 | Read/write events and analytics |
| Operator | `OPERATOR` | 3 | Alert management and incident response |
| Report Manager | `REPORT_MANAGER` | 4 | Report generation only |
| Viewer | `VIEWER` | 5 | Read-only |

## Permission Matrix

| Permission | ORG_ADMIN | ANALYST | OPERATOR | REPORT_MANAGER | VIEWER |
|---|---|---|---|---|---|
| `ORGANIZATION_READ` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `ORGANIZATION_MANAGE` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `MEMBER_INVITE` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `MEMBER_MANAGE` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `EVENTS_READ` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `EVENTS_WRITE` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `ANALYTICS_READ` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `ALERTS_READ` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `ALERTS_MANAGE` | ✅ | ✅ | ✅ | ❌ | ❌ |
| `REPORTS_READ` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `REPORTS_CREATE` | ✅ | ✅ | ❌ | ✅ | ❌ |
| `BILLING_READ` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `BILLING_MANAGE` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `WEBHOOKS_MANAGE` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `API_KEYS_MANAGE` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `SYSTEM_ADMIN` | ❌ | ❌ | ❌ | ❌ | ❌ |

> SUPER_ADMIN implicitly has all permissions.

## Usage — Protecting Endpoints

```python
from app.api.auth_deps import require_permission
from app.services.auth.rbac import Permission

@router.get("/sensitive-data")
def get_sensitive(
    tenant_context: dict = Depends(require_permission(Permission.EVENTS_READ))
):
    org_id = tenant_context["organization_id"]
    user = tenant_context["user"]
    ...
```

## `TenantContext` Structure

```python
{
    "user": User,                    # Authenticated SQLAlchemy User model
    "organization": Organization,    # Active Organization model
    "organization_id": int,          # Active org primary key
    "role": Role,                    # Role enum
    "permissions": List[Permission], # Resolved permission list
    "is_superadmin": bool
}
```

## API Key Authentication

API keys bypass JWT and provide programmatic access with scoped permissions:

```
X-API-Key: inf_live_<prefix>.<secret>
```

Keys are validated by:
1. Looking up `key_prefix` in DB
2. SHA-256 hashing the secret and comparing with `hashed_secret`
3. Checking `revoked_at IS NULL` and `expires_at > now`
4. Resolving `permissions_json` as the permission set
