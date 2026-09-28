# InfernoX Billing & Subscription

## Plan Tiers

| Plan | Price (INR/mo) | Events | Facilities | API Calls | Reports |
|------|---------------|--------|------------|-----------|---------|
| **Free** | ₹0 | 10,000 | 5 | 1,000 | 5 |
| **Pro** | ₹4,999 | 500,000 | 100 | 100,000 | 50 |
| **Enterprise** | ₹29,999 | Unlimited | Unlimited | 1,000,000 | Unlimited |

## Razorpay Integration Flow

```
Frontend: BillingModal selects plan
  ↓
POST /api/v1/billing/create-order (backend creates Razorpay Order)
  ↓
Razorpay Checkout JS opens payment modal
  ↓
User pays → Razorpay calls payment_handler
  ↓
POST /api/v1/billing/verify-payment (HMAC signature verify)
  ↓
Update Subscription.plan_tier + Organization.plan_tier
  ↓
Return success to frontend
```

## Webhook-Driven State Sync

Razorpay also sends webhooks for:
- `payment.authorized` → activate subscription
- `subscription.charged` → renew
- `subscription.cancelled` → downgrade

```
POST /api/v1/billing/razorpay-webhook
  → HMAC verify X-Razorpay-Signature
  → Update Subscription.status
  → Audit log
```

## Usage Metering

Usage is tracked per `billing_period` (YYYY-MM) per `metric`:

| Metric | Tracked on |
|--------|-----------|
| `events_processed` | Every FIRMS batch |
| `active_facilities` | Nightly snapshot |
| `alerts_generated` | Every alert created |
| `reports_generated` | Every report saved |
| `api_requests` | API key requests |

### Usage Limit Enforcement
```python
from app.services.billing.razorpay_provider import check_plan_limit

allowed, current, limit = check_plan_limit(db, org, "events_processed")
if not allowed:
    raise HTTPException(429, f"Limit reached: {current}/{limit}")
```

## Subscription States

| Status | Description |
|--------|-------------|
| `ACTIVE` | Currently paying or free tier |
| `TRIALING` | Trial period |
| `PAST_DUE` | Payment failed, grace period |
| `CANCELLED` | Cancelled at period end |
