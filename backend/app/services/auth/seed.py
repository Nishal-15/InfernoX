"""
InfernoX Phase 9: Default SaaS Seed Data
Initializes default Superadmin, Demo Organization, and initial Pro plan subscriptions for dev/test.
"""

from sqlalchemy.orm import Session
from datetime import datetime, timezone
import structlog

from app.models.saas import User, Organization, OrganizationMember, Subscription
from app.core.security import hash_password
from app.services.auth.rbac import Role

logger = structlog.get_logger(__name__)


def seed_saas_defaults(db: Session) -> None:
    """
    Seeds default Superadmin and Demo Organization if database is empty.
    """
    # 1. Superadmin account
    superadmin = db.query(User).filter(User.email == "admin@infernox.ai").first()
    if not superadmin:
        logger.info("seeding_default_superadmin")
        superadmin = User(
            email="admin@infernox.ai",
            full_name="InfernoX Platform Administrator",
            password_hash=hash_password("Admin@InfernoX2026!"),
            status="ACTIVE",
            email_verified=True,
            is_superadmin=True
        )
        db.add(superadmin)
        db.flush()

    # 2. Demo Organization
    demo_org = db.query(Organization).filter(Organization.slug == "demo-aerospace").first()
    if not demo_org:
        logger.info("seeding_demo_organization")
        demo_org = Organization(
            name="Demo Aerospace & Thermal Ops",
            slug="demo-aerospace",
            status="ACTIVE",
            plan="pro"
        )
        db.add(demo_org)
        db.flush()

        # Link Superadmin to Demo Org as ORG_ADMIN
        admin_membership = OrganizationMember(
            user_id=superadmin.id,
            organization_id=demo_org.id,
            role=Role.ORG_ADMIN.value,
            status="ACTIVE"
        )
        db.add(admin_membership)

        # Demo analyst user
        demo_user = db.query(User).filter(User.email == "analyst@infernox.ai").first()
        if not demo_user:
            demo_user = User(
                email="analyst@infernox.ai",
                full_name="Lead Thermal Analyst",
                password_hash=hash_password("Analyst@InfernoX2026!"),
                status="ACTIVE",
                email_verified=True,
                is_superadmin=False
            )
            db.add(demo_user)
            db.flush()

            analyst_membership = OrganizationMember(
                user_id=demo_user.id,
                organization_id=demo_org.id,
                role=Role.ANALYST.value,
                status="ACTIVE"
            )
            db.add(analyst_membership)

        # Demo Subscription
        sub = Subscription(
            organization_id=demo_org.id,
            plan="pro",
            status="ACTIVE",
            billing_email="admin@infernox.ai"
        )
        db.add(sub)

    db.commit()
