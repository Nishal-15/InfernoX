"""
InfernoX Phase 9: Authentication Endpoints
Production-grade registration, Argon2id password authentication, JWT session issuing,
user profile, and invitation acceptance.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import structlog

from app.db.session import get_db
from app.models.saas import (
    User, Organization, OrganizationMember, OrganizationInvitation,
    Subscription, PlatformAuditLog
)
from app.schemas.saas import (
    UserCreate, UserLogin, UserResponse, TokenResponse,
    InvitationAccept
)
from app.core.security import (
    hash_password, verify_password, create_access_token
)
from app.core.config import settings
from app.services.auth.rbac import Role, get_role_permissions
from app.api.auth_deps import get_current_user

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    payload: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Register a new user account, hash password with Argon2id, create their initial organization
    and assign them the ORG_ADMIN role.
    """
    existing_user = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists."
        )

    # 1. Create User
    new_user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        status="ACTIVE",
        email_verified=True,  # In demo/dev mode auto-verified
        is_superadmin=False,
        last_login_at=datetime.now(timezone.utc)
    )
    db.add(new_user)
    db.flush()

    # 2. Create Initial Organization
    org_name = payload.organization_name or f"{payload.full_name}'s Workspace"
    org_slug = org_name.lower().replace(" ", "-")[:40]
    new_org = Organization(
        name=org_name,
        slug=org_slug,
        status="ACTIVE",
        plan="free"
    )
    db.add(new_org)
    db.flush()

    # 3. Create Organization Member (ORG_ADMIN)
    member = OrganizationMember(
        user_id=new_user.id,
        organization_id=new_org.id,
        role=Role.ORG_ADMIN.value,
        status="ACTIVE"
    )
    db.add(member)

    # 4. Create Initial Subscription (Free)
    sub = Subscription(
        organization_id=new_org.id,
        plan="free",
        status="ACTIVE",
        billing_email=new_user.email
    )
    db.add(sub)

    # 5. Audit Log
    audit = PlatformAuditLog(
        actor_id=new_user.id,
        actor_email=new_user.email,
        organization_id=new_org.id,
        action="user.registered",
        resource_type="User",
        resource_id=new_user.id,
        details={"org_id": new_org.id, "org_name": org_name}
    )
    db.add(audit)

    db.commit()
    db.refresh(new_user)

    # Generate JWT
    token_claims = {
        "sub": str(new_user.id),
        "email": new_user.email,
        "is_superadmin": new_user.is_superadmin,
        "organization_id": new_org.id,
        "role": Role.ORG_ADMIN.value
    }
    access_token = create_access_token(token_claims)
    perms = get_role_permissions(Role.ORG_ADMIN.value)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(new_user),
        active_organization_id=new_org.id,
        role=Role.ORG_ADMIN.value,
        permissions=perms
    )


@router.post("/login", response_model=TokenResponse)
def login_user(
    payload: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Authenticate with email and password via Argon2id.
    Returns JWT access token with user claims and default organization context.
    """
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    if user.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is suspended or deactivated. Contact your administrator."
        )

    user.last_login_at = datetime.now(timezone.utc)

    # Find primary or first active membership
    primary_membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id,
        OrganizationMember.status == "ACTIVE"
    ).first()

    org_id = primary_membership.organization_id if primary_membership else None
    role_val = primary_membership.role if primary_membership else (Role.SUPER_ADMIN.value if user.is_superadmin else Role.VIEWER.value)

    token_claims = {
        "sub": str(user.id),
        "email": user.email,
        "is_superadmin": user.is_superadmin,
        "organization_id": org_id,
        "role": role_val
    }
    access_token = create_access_token(token_claims)
    perms = get_role_permissions(role_val)

    # Audit log
    audit = PlatformAuditLog(
        actor_id=user.id,
        actor_email=user.email,
        organization_id=org_id,
        action="user.login",
        resource_type="User",
        resource_id=user.id
    )
    db.add(audit)
    db.commit()

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
        active_organization_id=org_id,
        role=role_val,
        permissions=perms
    )


@router.get("/me")
def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns current authenticated user details and all active organization memberships.
    """
    memberships = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.status == "ACTIVE"
    ).all()

    org_list = []
    for m in memberships:
        org = db.query(Organization).filter(Organization.id == m.organization_id).first()
        if org:
            org_list.append({
                "organization_id": org.id,
                "name": org.name,
                "slug": org.slug,
                "plan": org.plan,
                "role": m.role,
                "permissions": get_role_permissions(m.role)
            })

    return {
        "user": UserResponse.model_validate(current_user),
        "organizations": org_list
    }


@router.post("/logout")
def logout_user(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Logout current user session and record audit trail.
    """
    audit = PlatformAuditLog(
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="user.logout",
        resource_type="User",
        resource_id=current_user.id
    )
    db.add(audit)
    db.commit()
    return {"message": "Successfully logged out."}


@router.post("/invitations/accept", response_model=TokenResponse)
def accept_invitation(
    payload: InvitationAccept,
    db: Session = Depends(get_db)
):
    """
    Accept an organization invitation token, set up user credentials, and join organization.
    """
    invitation = db.query(OrganizationInvitation).filter(
        OrganizationInvitation.token == payload.token,
        OrganizationInvitation.accepted == False
    ).first()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or already accepted invitation token."
        )

    if invitation.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation token has expired. Please request a new invitation."
        )

    # Check if user already exists
    user = db.query(User).filter(User.email == invitation.email.lower()).first()
    if not user:
        user = User(
            email=invitation.email.lower(),
            full_name=payload.full_name,
            password_hash=hash_password(payload.password),
            status="ACTIVE",
            email_verified=True,
            last_login_at=datetime.now(timezone.utc)
        )
        db.add(user)
        db.flush()

    # Create membership
    member = OrganizationMember(
        user_id=user.id,
        organization_id=invitation.organization_id,
        role=invitation.role,
        status="ACTIVE"
    )
    db.add(member)

    invitation.accepted = True
    invitation.accepted_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(user)

    token_claims = {
        "sub": str(user.id),
        "email": user.email,
        "is_superadmin": user.is_superadmin,
        "organization_id": invitation.organization_id,
        "role": invitation.role
    }
    access_token = create_access_token(token_claims)
    perms = get_role_permissions(invitation.role)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
        active_organization_id=invitation.organization_id,
        role=invitation.role,
        permissions=perms
    )
