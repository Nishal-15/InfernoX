"""
InfernoX Phase 9: Organization Management Endpoints
Multi-tenant administration: profiles, members, invitations, API keys, webhooks.
Strict server-side tenant isolation and RBAC permission enforcement.
"""

from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import structlog

from app.db.session import get_db
from app.models.saas import (
    User, Organization, OrganizationMember, OrganizationInvitation,
    ApiKey, WebhookEndpoint, PlatformAuditLog
)
from app.schemas.saas import (
    OrganizationCreate, OrganizationResponse, OrganizationUpdate,
    OrganizationMemberOut, MemberRoleUpdate, InvitationCreate, InvitationResponse,
    ApiKeyCreate, ApiKeyResponse, ApiKeyCreatedResponse,
    WebhookCreate, WebhookResponse, WebhookUpdate
)
from app.core.security import (
    generate_api_key, hash_api_key_secret, generate_invitation_token,
    generate_webhook_secret
)
from app.services.auth.rbac import Permission, Role, get_role_permissions
from app.api.auth_deps import (
    get_current_user, get_current_tenant, require_permission
)
from app.services.billing.razorpay_provider import check_plan_limit
from app.services.email.provider import get_email_provider

logger = structlog.get_logger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------
# Tenant Switcher & Organization Profiles
# ---------------------------------------------------------------------

@router.get("/", response_model=List[OrganizationResponse])
def list_user_organizations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns all organizations the current authenticated user belongs to.
    Used by the Tenant Switcher.
    """
    memberships = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.status == "ACTIVE"
    ).all()

    org_ids = [m.organization_id for m in memberships]
    orgs = db.query(Organization).filter(Organization.id.in_(org_ids)).all()
    return orgs


@router.post("/", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
def create_organization(
    payload: OrganizationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Creates a new organization and assigns the creator as ORG_ADMIN.
    """
    slug = (payload.slug or payload.name).lower().replace(" ", "-")[:40]
    org = Organization(
        name=payload.name,
        slug=slug,
        status="ACTIVE",
        plan=payload.plan or "free"
    )
    db.add(org)
    db.flush()

    member = OrganizationMember(
        user_id=current_user.id,
        organization_id=org.id,
        role=Role.ORG_ADMIN.value,
        status="ACTIVE"
    )
    db.add(member)

    audit = PlatformAuditLog(
        actor_id=current_user.id,
        actor_email=current_user.email,
        organization_id=org.id,
        action="organization.created",
        resource_type="Organization",
        resource_id=org.id,
        details={"name": org.name, "plan": org.plan}
    )
    db.add(audit)

    db.commit()
    db.refresh(org)
    return org


@router.get("/current", response_model=OrganizationResponse)
def get_current_organization_profile(
    tenant_context: dict = Depends(get_current_tenant)
):
    """
    Get active tenant profile details.
    """
    return tenant_context["organization"]


@router.patch("/current", response_model=OrganizationResponse)
def update_current_organization_profile(
    payload: OrganizationUpdate,
    tenant_context: dict = Depends(require_permission(Permission.ORGANIZATION_MANAGE)),
    db: Session = Depends(get_db)
):
    """
    Update active tenant profile settings and custom region.
    """
    org: Organization = tenant_context["organization"]
    user: User = tenant_context["user"]

    if payload.name:
        org.name = payload.name
    if payload.custom_region is not None:
        org.custom_region = payload.custom_region
    if payload.settings is not None:
        org.settings = payload.settings

    org.updated_at = datetime.now(timezone.utc)

    audit = PlatformAuditLog(
        actor_id=user.id,
        actor_email=user.email,
        organization_id=org.id,
        action="organization.updated",
        resource_type="Organization",
        resource_id=org.id,
        details=payload.model_dump(exclude_unset=True)
    )
    db.add(audit)

    db.commit()
    db.refresh(org)
    return org


# ---------------------------------------------------------------------
# Member Management & RBAC
# ---------------------------------------------------------------------

@router.get("/members", response_model=List[OrganizationMemberOut])
def list_organization_members(
    tenant_context: dict = Depends(require_permission(Permission.USERS_READ)),
    db: Session = Depends(get_db)
):
    """
    Lists all members and their roles for the current organization.
    """
    org_id = tenant_context["organization_id"]
    members = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == org_id
    ).all()

    out = []
    for m in members:
        user = db.query(User).filter(User.id == m.user_id).first()
        out.append(OrganizationMemberOut(
            id=m.id,
            user_id=m.user_id,
            organization_id=m.organization_id,
            role=m.role,
            status=m.status,
            user_email=user.email if user else None,
            user_name=user.full_name if user else None,
            created_at=m.created_at
        ))
    return out


@router.patch("/members/{member_id}/role")
def update_member_role(
    member_id: str,
    payload: MemberRoleUpdate,
    tenant_context: dict = Depends(require_permission(Permission.USERS_MANAGE)),
    db: Session = Depends(get_db)
):
    """
    Updates a team member's RBAC role within the organization.
    """
    org_id = tenant_context["organization_id"]
    user: User = tenant_context["user"]

    member = db.query(OrganizationMember).filter(
        OrganizationMember.id == member_id,
        OrganizationMember.organization_id == org_id
    ).first()

    if not member:
        raise HTTPException(status_code=404, detail="Member not found in this organization.")

    old_role = member.role
    member.role = payload.role

    audit = PlatformAuditLog(
        actor_id=user.id,
        actor_email=user.email,
        organization_id=org_id,
        action="member.role_updated",
        resource_type="OrganizationMember",
        resource_id=member.id,
        details={"target_user_id": member.user_id, "old_role": old_role, "new_role": payload.role}
    )
    db.add(audit)
    db.commit()

    return {"message": "Member role updated successfully", "member_id": member.id, "new_role": payload.role}


@router.delete("/members/{member_id}")
def remove_member(
    member_id: str,
    tenant_context: dict = Depends(require_permission(Permission.USERS_MANAGE)),
    db: Session = Depends(get_db)
):
    """
    Removes a member from the organization.
    """
    org_id = tenant_context["organization_id"]
    user: User = tenant_context["user"]

    member = db.query(OrganizationMember).filter(
        OrganizationMember.id == member_id,
        OrganizationMember.organization_id == org_id
    ).first()

    if not member:
        raise HTTPException(status_code=404, detail="Member not found in this organization.")

    if member.user_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself as an organization member.")

    db.delete(member)

    audit = PlatformAuditLog(
        actor_id=user.id,
        actor_email=user.email,
        organization_id=org_id,
        action="member.removed",
        resource_type="OrganizationMember",
        resource_id=member_id,
        details={"removed_user_id": member.user_id}
    )
    db.add(audit)
    db.commit()

    return {"message": "Member successfully removed from organization"}


# ---------------------------------------------------------------------
# Invitations
# ---------------------------------------------------------------------

@router.post("/invitations", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
def invite_member(
    payload: InvitationCreate,
    tenant_context: dict = Depends(require_permission(Permission.USERS_MANAGE)),
    db: Session = Depends(get_db)
):
    """
    Invites a new colleague to join the organization under a specific RBAC role.
    Checks plan limits (max_users) before sending invitation.
    """
    org: Organization = tenant_context["organization"]
    user: User = tenant_context["user"]

    # Check Plan Limit
    allowed, msg = check_plan_limit(db, org.id, "users", 1)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=msg)

    # Check if already a member
    existing_user = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing_user:
        already_member = db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.user_id == existing_user.id
        ).first()
        if already_member:
            raise HTTPException(status_code=400, detail="User is already a member of this organization.")

    token = generate_invitation_token()
    invitation = OrganizationInvitation(
        organization_id=org.id,
        email=payload.email.lower(),
        role=payload.role,
        token=token,
        invited_by_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        accepted=False
    )
    db.add(invitation)

    audit = PlatformAuditLog(
        actor_id=user.id,
        actor_email=user.email,
        organization_id=org.id,
        action="invitation.created",
        resource_type="OrganizationInvitation",
        resource_id=invitation.id,
        details={"email": payload.email.lower(), "role": payload.role}
    )
    db.add(audit)
    db.commit()
    db.refresh(invitation)

    # Dispatch email
    email_provider = get_email_provider()
    email_provider.send_template(
        to_email=payload.email,
        template_name="invitation",
        context={
            "organization_name": org.name,
            "inviter_name": user.full_name,
            "role": payload.role,
            "token": token
        }
    )

    return invitation


@router.get("/invitations", response_model=List[InvitationResponse])
def list_pending_invitations(
    tenant_context: dict = Depends(require_permission(Permission.USERS_MANAGE)),
    db: Session = Depends(get_db)
):
    """
    Lists pending, unaccepted invitations for this organization.
    """
    org_id = tenant_context["organization_id"]
    return db.query(OrganizationInvitation).filter(
        OrganizationInvitation.organization_id == org_id,
        OrganizationInvitation.accepted == False
    ).all()


# ---------------------------------------------------------------------
# API Keys (Headless Integrations)
# ---------------------------------------------------------------------

@router.get("/api-keys", response_model=List[ApiKeyResponse])
def list_api_keys(
    tenant_context: dict = Depends(require_permission(Permission.ORGANIZATION_READ)),
    db: Session = Depends(get_db)
):
    """
    List API keys configured for the active organization.
    Secrets are never stored or returned in plaintext.
    """
    org_id = tenant_context["organization_id"]
    return db.query(ApiKey).filter(
        ApiKey.organization_id == org_id,
        ApiKey.revoked_at.is_(None)
    ).all()


@router.post("/api-keys", response_model=ApiKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(
    payload: ApiKeyCreate,
    tenant_context: dict = Depends(require_permission(Permission.ORGANIZATION_MANAGE)),
    db: Session = Depends(get_db)
):
    """
    Generates a secure API key with prefix.
    Only the SHA-256 hash is saved to the database.
    The raw API key is returned exactly ONCE in this response.
    """
    org: Organization = tenant_context["organization"]
    user: User = tenant_context["user"]

    raw_key, prefix, secret = generate_api_key()
    hashed_secret = hash_api_key_secret(secret)
    expires_at = datetime.now(timezone.utc) + timedelta(days=payload.expires_in_days or 365)

    api_key_obj = ApiKey(
        organization_id=org.id,
        name=payload.name,
        key_prefix=prefix,
        hashed_secret=hashed_secret,
        permissions=payload.permissions,
        created_by_id=user.id,
        expires_at=expires_at,
        is_active=True
    )
    db.add(api_key_obj)

    audit = PlatformAuditLog(
        actor_id=user.id,
        actor_email=user.email,
        organization_id=org.id,
        action="api_key.created",
        resource_type="ApiKey",
        resource_id=api_key_obj.id,
        details={"name": payload.name, "prefix": prefix, "permissions": payload.permissions}
    )
    db.add(audit)
    db.commit()
    db.refresh(api_key_obj)

    return ApiKeyCreatedResponse(
        id=api_key_obj.id,
        organization_id=api_key_obj.organization_id,
        name=api_key_obj.name,
        key_prefix=api_key_obj.key_prefix,
        permissions=api_key_obj.permissions,
        is_active=api_key_obj.is_active,
        created_at=api_key_obj.created_at,
        expires_at=api_key_obj.expires_at,
        last_used_at=api_key_obj.last_used_at,
        raw_api_key=raw_key
    )


@router.delete("/api-keys/{key_id}")
def revoke_api_key(
    key_id: str,
    tenant_context: dict = Depends(require_permission(Permission.ORGANIZATION_MANAGE)),
    db: Session = Depends(get_db)
):
    """
    Revokes an active API key immediately.
    """
    org_id = tenant_context["organization_id"]
    user: User = tenant_context["user"]

    key_obj = db.query(ApiKey).filter(
        ApiKey.id == key_id,
        ApiKey.organization_id == org_id
    ).first()

    if not key_obj:
        raise HTTPException(status_code=404, detail="API key not found.")

    key_obj.is_active = False
    key_obj.revoked_at = datetime.now(timezone.utc)

    audit = PlatformAuditLog(
        actor_id=user.id,
        actor_email=user.email,
        organization_id=org_id,
        action="api_key.revoked",
        resource_type="ApiKey",
        resource_id=key_id,
        details={"name": key_obj.name, "prefix": key_obj.key_prefix}
    )
    db.add(audit)
    db.commit()

    return {"message": "API key successfully revoked", "id": key_id}


# ---------------------------------------------------------------------
# Webhooks
# ---------------------------------------------------------------------

@router.get("/webhooks", response_model=List[WebhookResponse])
def list_webhooks(
    tenant_context: dict = Depends(require_permission(Permission.ORGANIZATION_READ)),
    db: Session = Depends(get_db)
):
    """
    List configured webhook endpoints for the active organization.
    """
    org_id = tenant_context["organization_id"]
    return db.query(WebhookEndpoint).filter(WebhookEndpoint.organization_id == org_id).all()


@router.post("/webhooks", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
def create_webhook(
    payload: WebhookCreate,
    tenant_context: dict = Depends(require_permission(Permission.ORGANIZATION_MANAGE)),
    db: Session = Depends(get_db)
):
    """
    Registers a new outbound webhook with auto-generated HMAC secret.
    """
    org_id = tenant_context["organization_id"]
    user: User = tenant_context["user"]

    secret = generate_webhook_secret()
    ep = WebhookEndpoint(
        organization_id=org_id,
        url=payload.url,
        secret=secret,
        subscribed_events=payload.subscribed_events,
        is_active=True,
        description=payload.description
    )
    db.add(ep)

    audit = PlatformAuditLog(
        actor_id=user.id,
        actor_email=user.email,
        organization_id=org_id,
        action="webhook.created",
        resource_type="WebhookEndpoint",
        resource_id=ep.id,
        details={"url": payload.url, "events": payload.subscribed_events}
    )
    db.add(audit)
    db.commit()
    db.refresh(ep)

    return ep


@router.delete("/webhooks/{webhook_id}")
def delete_webhook(
    webhook_id: str,
    tenant_context: dict = Depends(require_permission(Permission.ORGANIZATION_MANAGE)),
    db: Session = Depends(get_db)
):
    """
    Deletes a registered webhook endpoint.
    """
    org_id = tenant_context["organization_id"]
    user: User = tenant_context["user"]

    ep = db.query(WebhookEndpoint).filter(
        WebhookEndpoint.id == webhook_id,
        WebhookEndpoint.organization_id == org_id
    ).first()

    if not ep:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found.")

    db.delete(ep)

    audit = PlatformAuditLog(
        actor_id=user.id,
        actor_email=user.email,
        organization_id=org_id,
        action="webhook.deleted",
        resource_type="WebhookEndpoint",
        resource_id=webhook_id,
        details={"url": ep.url}
    )
    db.add(audit)
    db.commit()

    return {"message": "Webhook successfully deleted", "id": webhook_id}
