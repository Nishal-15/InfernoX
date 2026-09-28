"""
InfernoX Phase 9: Billing & Razorpay Endpoints
Handles subscription plans, checkout orders, payment verification,
Razorpay webhook processing with HMAC signatures, and usage metering.
"""

from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, Header, status
from sqlalchemy.orm import Session
import structlog

from app.db.session import get_db
from app.models.saas import Organization, Subscription, PlatformAuditLog
from app.schemas.saas import (
    SubscriptionResponse, RazorpayOrderCreate, RazorpayCheckoutResponse,
    RazorpayPaymentVerify, UsageResponse
)
from app.services.auth.rbac import Permission
from app.api.auth_deps import get_current_tenant, require_permission
from app.services.billing.razorpay_provider import (
    PLANS, razorpay_provider, get_organization_usage
)

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/plans")
def list_available_plans():
    """
    Returns public pricing tiers, limits, and capabilities.
    """
    return list(PLANS.values())


@router.get("/subscription", response_model=SubscriptionResponse)
def get_current_subscription(
    tenant_context: dict = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Returns current organization's active subscription status, plan tier, and renewal date.
    """
    org_id = tenant_context["organization_id"]
    sub = db.query(Subscription).filter(Subscription.organization_id == org_id).first()

    if not sub:
        # Create default free subscription if none exists
        sub = Subscription(
            organization_id=org_id,
            plan="free",
            status="ACTIVE"
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)

    return sub


@router.post("/create-order", response_model=RazorpayCheckoutResponse)
def create_subscription_order(
    payload: RazorpayOrderCreate,
    tenant_context: dict = Depends(require_permission(Permission.BILLING_MANAGE)),
    db: Session = Depends(get_db)
):
    """
    Creates a Razorpay order for subscription upgrade or renewal.
    Never exposes API secrets to client.
    """
    org: Organization = tenant_context["organization"]
    user = tenant_context["user"]

    try:
        order_info = razorpay_provider.create_order(
            organization_id=org.id,
            plan=payload.plan,
            billing_cycle=payload.billing_cycle
        )
    except Exception as e:
        logger.error("razorpay_order_creation_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to initialize checkout order with payment provider.")

    return RazorpayCheckoutResponse(
        order_id=order_info["order_id"],
        razorpay_key_id=order_info["razorpay_key_id"],
        amount=order_info["amount"],
        currency=order_info["currency"],
        plan=order_info["plan"],
        billing_cycle=order_info["billing_cycle"],
        organization_id=org.id,
        prefill_name=user.full_name,
        prefill_email=user.email
    )


@router.post("/verify-payment")
def verify_subscription_payment(
    payload: RazorpayPaymentVerify,
    tenant_context: dict = Depends(require_permission(Permission.BILLING_MANAGE)),
    db: Session = Depends(get_db)
):
    """
    Verifies Razorpay payment signature and activates the chosen plan for the organization.
    """
    org: Organization = tenant_context["organization"]
    user = tenant_context["user"]

    is_valid = razorpay_provider.verify_payment_signature(
        order_id=payload.razorpay_order_id,
        payment_id=payload.razorpay_payment_id,
        signature=payload.razorpay_signature
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment verification failed: invalid signature."
        )

    # Update organization plan
    org.plan = payload.plan
    org.updated_at = datetime.now(timezone.utc)

    # Update or create subscription
    sub = db.query(Subscription).filter(Subscription.organization_id == org.id).first()
    now_utc = datetime.now(timezone.utc)
    if not sub:
        sub = Subscription(organization_id=org.id)
        db.add(sub)

    sub.plan = payload.plan
    sub.status = "ACTIVE"
    sub.current_period_start = now_utc
    sub.current_period_end = now_utc + timedelta(days=30)
    sub.razorpay_subscription_id = payload.razorpay_order_id
    sub.updated_at = now_utc

    audit = PlatformAuditLog(
        actor_id=user.id,
        actor_email=user.email,
        organization_id=org.id,
        action="billing.payment_verified",
        resource_type="Subscription",
        resource_id=sub.id,
        details={
            "plan": payload.plan,
            "order_id": payload.razorpay_order_id,
            "payment_id": payload.razorpay_payment_id
        }
    )
    db.add(audit)
    db.commit()

    return {
        "status": "success",
        "message": f"Successfully upgraded organization to {payload.plan.upper()} tier!",
        "plan": payload.plan,
        "active_until": sub.current_period_end.isoformat()
    }


@router.post("/razorpay-webhook")
async def handle_razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Authoritative server-to-server webhook from Razorpay for payment states.
    Validates HMAC signature.
    """
    body_bytes = await request.body()

    if not x_razorpay_signature:
        raise HTTPException(status_code=400, detail="Missing X-Razorpay-Signature header.")

    is_valid = razorpay_provider.verify_webhook_signature(body_bytes, x_razorpay_signature)
    if not is_valid:
        logger.warning("razorpay_webhook_signature_mismatch")
        raise HTTPException(status_code=400, detail="Invalid webhook signature.")

    try:
        import json
        payload = json.loads(body_bytes.decode("utf-8"))
        event_name = payload.get("event")
        entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        notes = entity.get("notes", {})
        org_id = notes.get("organization_id")
        plan = notes.get("plan")

        logger.info("razorpay_webhook_received", event=event_name, org_id=org_id, plan=plan)

        if org_id and event_name in ["payment.captured", "order.paid"]:
            sub = db.query(Subscription).filter(Subscription.organization_id == org_id).first()
            if sub:
                sub.status = "ACTIVE"
                sub.current_period_end = datetime.now(timezone.utc) + timedelta(days=30)
                if plan:
                    sub.plan = plan
                    org = db.query(Organization).filter(Organization.id == org_id).first()
                    if org:
                        org.plan = plan
                db.commit()

        return {"status": "ok", "received_event": event_name}
    except Exception as e:
        logger.error("razorpay_webhook_processing_error", error=str(e))
        return {"status": "error", "detail": str(e)}


@router.get("/usage", response_model=UsageResponse)
def get_current_usage(
    tenant_context: dict = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Returns real-time usage statistics and plan limits calculated from actual database entities.
    """
    org_id = tenant_context["organization_id"]
    return get_organization_usage(db, org_id)
