# InfernoX Multi-Tenancy Architecture

## Overview

InfernoX Phase 9 implements a full multi-tenant SaaS isolation model, separating **Global Intelligence** (NASA FIRMS data, OSM facilities, WorldCover) from **Tenant-Scoped Data** (custom alert rules, private facilities, reports, API keys, webhooks).

## Tenant Hierarchy

```
Platform (InfernoX)
  └── Organization (Tenant)
        ├── Users (via OrganizationMember)
        ├── API Keys
        ├── Webhook Endpoints
        ├── Custom Alert Rules (org scoped)
        ├── Generated Reports
        └── Subscription
```

## Key Models

| Model | Description |
|-------|-------------|
| `User` | Platform identity with Argon2id password hash |
| `Organization` | Tenant workspace with billing plan |
| `OrganizationMember` | Role-based membership linking User→Organization |
| `OrganizationInvitation` | Secure invitation token (7-day TTL) |
| `ApiKey` | SHA-256 hashed headless credentials |
| `WebhookEndpoint` | HMAC-SHA256 outbound notification target |
| `Subscription` | Razorpay billing record |
| `UsageRecord` | Real-time metered usage per billing period |
| `PlatformAuditLog` | Immutable security event trail |

## Tenant Isolation Mechanisms

### API Layer
- All protected endpoints use `get_current_tenant()` dependency
- The `X-Organization-Id` header specifies the active workspace
- Users can only access organizations they are ACTIVE members of
- **Superadmins** can impersonate any organization context

### Data Layer
- `organization_id` foreign key on `AlertRule`, `Alert`, `GeneratedReport`
- All queries in org-scoped endpoints filter by `organization_id`
- Global intelligence data (FIRMS events, OSM facilities) is read-only across tenants

### WebSocket Layer
- Each connection is tagged with an `organization_id`
- Broadcasts filter recipients by organization, preventing event leakage between tenants

## Registration Flow

```
POST /api/v1/auth/register
  → Create User (Argon2id hash)
  → Create Organization
  → Create OrganizationMember (role=ORG_ADMIN)
  → Create Subscription (plan=free)
  → Create PlatformAuditLog
  → Return JWT access token
```

## Invitation Flow

```
POST /api/v1/organizations/invitations (by ORG_ADMIN)
  → Generate secure token (32-byte URL-safe random)
  → Send email via ConsoleEmailProvider or SMTPEmailProvider
  → Token valid for 7 days

POST /api/v1/auth/invitations/accept (by invitee)
  → Validate token and expiry
  → Create/link User account
  → Create OrganizationMember
  → Mark invitation accepted
  → Return JWT
```
