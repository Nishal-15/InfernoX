from datetime import datetime, timezone
from typing import Optional, Tuple
from fastapi import Depends, HTTPException, status, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.security import decode_access_token, hash_api_key
from app.models.saas import User, Organization, OrganizationMember, ApiKey
from app.services.auth.rbac import has_permission, Permission

security_scheme = HTTPBearer(auto_error=False)


class TenantContext(dict):
    """
    Dual-interface tenant context supporting both dictionary lookup:
      tenant_context["organization"], tenant_context["user"], tenant_context["organization_id"]
    and tuple unpacking:
      user, org, membership = tenant_context
    """
    def __init__(self, user: User, organization: Organization, membership: OrganizationMember):
        super().__init__({
            "user": user,
            "organization": organization,
            "membership": membership,
            "organization_id": organization.id,
            "role": membership.role
        })
        self.user = user
        self.organization = organization
        self.membership = membership
        self.organization_id = organization.id
        self.role = membership.role

    def __iter__(self):
        yield self["user"]
        yield self["organization"]
        yield self["membership"]


def get_current_user(
    request: Request,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Extracts and authenticates current user from Bearer header or HTTP-only cookie.
    """
    token: Optional[str] = None
    if auth and auth.credentials:
        token = auth.credentials
    elif "authorization" in request.headers:
        auth_hdr = request.headers.get("authorization", "")
        if auth_hdr.lower().startswith("bearer "):
            token = auth_hdr[7:].strip()
    elif "access_token" in request.cookies:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials not provided",
            headers={"WWW-Authenticate": "Bearer"}
        )

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user_id = int(payload["sub"])
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user record not found",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if user.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User account is {user.status.lower()}"
        )

    return user


def get_current_tenant(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    x_org_id: Optional[str] = Header(None, alias="X-Organization-Id")
) -> TenantContext:
    """
    Resolves the active organization / tenant context for the authenticated user.
    Enforces strict tenant isolation: users cannot access organizations they do not belong to.
    """
    org_id_int: Optional[int] = None
    if x_org_id:
        try:
            org_id_int = int(x_org_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid organization ID header format"
            )

    membership: Optional[OrganizationMember] = None

    if org_id_int is not None:
        membership = db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == org_id_int,
            OrganizationMember.user_id == user.id,
            OrganizationMember.status == "ACTIVE"
        ).first()

        # Allow platform superadmins to act in organization context even without direct membership
        if not membership and user.is_superadmin:
            target_org = db.query(Organization).filter(Organization.id == org_id_int).first()
            if target_org:
                mock_member = OrganizationMember(
                    organization_id=target_org.id,
                    user_id=user.id,
                    role="SUPER_ADMIN",
                    status="ACTIVE"
                )
                return TenantContext(user, target_org, mock_member)

        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to organization: you do not possess active membership in the specified organization"
            )
    else:
        # Default to user's first active organization membership
        membership = db.query(OrganizationMember).filter(
            OrganizationMember.user_id == user.id,
            OrganizationMember.status == "ACTIVE"
        ).first()

        if not membership:
            if user.is_superadmin:
                first_org = db.query(Organization).first()
                if first_org:
                    mock_member = OrganizationMember(
                        organization_id=first_org.id,
                        user_id=user.id,
                        role="SUPER_ADMIN",
                        status="ACTIVE"
                    )
                    return TenantContext(user, first_org, mock_member)

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No active organization membership associated with this user"
            )

    org = db.query(Organization).filter(Organization.id == membership.organization_id).first()
    if not org or org.status not in ["ACTIVE", "TRIAL"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Organization workspace is currently {org.status.lower() if org else 'unavailable'}"
        )

    return TenantContext(user, org, membership)


def require_permission(permission: str):
    """
    Factory creating a FastAPI dependency that verifies the active user's role
    possesses the specified granular RBAC permission.
    """
    def dependency(
        tenant_context: TenantContext = Depends(get_current_tenant)
    ) -> TenantContext:
        user = tenant_context["user"]
        org = tenant_context["organization"]
        membership = tenant_context["membership"]

        if user.is_superadmin or membership.role == "SUPER_ADMIN":
            return tenant_context

        if not has_permission(membership.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: role '{membership.role}' lacks required permission '{permission}'"
            )
        return tenant_context

    return dependency


def require_superadmin(user: User = Depends(get_current_user)) -> User:
    """
    Enforces that the authenticated user is a platform super administrator.
    """
    if not user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to platform Super Administrators"
        )
    return user


def get_api_key_tenant(
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> Tuple[Organization, ApiKey]:
    """
    Authenticates headless/API requests via hashed organization API key.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header"
        )

    hashed = hash_api_key(x_api_key)
    api_key_record = db.query(ApiKey).filter(
        ApiKey.hashed_secret == hashed,
        ApiKey.revoked_at.is_(None)
    ).first()

    if not api_key_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key"
        )

    now = datetime.now(timezone.utc)
    if api_key_record.expires_at and api_key_record.expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired"
        )

    org = db.query(Organization).filter(Organization.id == api_key_record.organization_id).first()
    if not org or org.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization associated with API key is not active"
        )

    api_key_record.last_used_at = now
    db.commit()

    return org, api_key_record
