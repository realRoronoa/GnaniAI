import uuid
from decimal import Decimal
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.enums import BillingCycle, OrgStatus, SubscriptionStatus, UserRole
from app.models.subscriptions import Subscription, SubscriptionPlan
from app.models.tenant import Organization, OrganizationLocation, OrganizationMembership, User

# In-memory SQLite engine with StaticPool for test isolation
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="module", autouse=True)
def setup_database() -> Generator[None, None, None]:
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# -----------------------------------------------------------------------------
# 1. Platform Owner Login, Plan Creation & Organization Onboarding
# -----------------------------------------------------------------------------
def test_platform_owner_workflow(client: TestClient, db_session: Session) -> None:
    # Seed platform owner
    superadmin = User(
        email="owner@arogyascribe.in",
        password_hash=get_password_hash("Owner@12345"),
        full_name="Platform Owner",
        is_super_admin=True,
        is_active=True,
    )
    db_session.add(superadmin)
    db_session.commit()

    # 1. Login
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@arogyascribe.in", "password": "Owner@12345"},
    )
    assert login_resp.status_code == 200, login_resp.text
    token_data = login_resp.json()
    access_token = token_data["access_token"]
    assert token_data["user"]["role"] == "PLATFORM_OWNER"
    headers = {"Authorization": f"Bearer {access_token}"}

    # 2. Create Subscription Plan
    plan_resp = client.post(
        "/api/v1/platform/plans",
        headers=headers,
        json={
            "name": "Micro Clinic",
            "code": "MICRO",
            "monthly_price": "1499.00",
            "annual_price": "14990.00",
            "max_doctors": 1,
            "max_receptionists": 1,
            "max_branches": 1,
            "monthly_consultation_limit": 100,
            "audio_storage_mb_limit": 500,
            "report_generation_limit": 100,
            "included_features_json": ["Basic SOAP"],
            "duration_days": 30,
            "trial_days": 7,
        },
    )
    assert plan_resp.status_code == 201, plan_resp.text
    plan_id = plan_resp.json()["id"]

    # 3. Onboard Organization + Org Admin
    org_resp = client.post(
        "/api/v1/platform/organizations",
        headers=headers,
        json={
            "name": "Apollo Care Whitefield",
            "org_type": "CLINIC",
            "contact_email": "admin@apollowhitefield.in",
            "contact_phone": "+919876543299",
            "address": "ITPB Main Road, Whitefield, Bengaluru",
            "registration_number": "KA-CL-2023-01",
            "admin_full_name": "Dr. Suresh Reddy",
            "admin_email": "suresh@apollowhitefield.in",
            "admin_password": "AdminPassword@123",
            "admin_phone": "+919876543298",
        },
    )
    assert org_resp.status_code == 201, org_resp.text
    org_data = org_resp.json()
    org_id = org_data["id"]
    assert org_data["name"] == "Apollo Care Whitefield"

    # 4. Activate Paid Subscription
    activate_resp = client.post(
        "/api/v1/platform/subscriptions/activate",
        headers=headers,
        json={
            "organization_id": org_id,
            "plan_id": plan_id,
            "billing_cycle": "MONTHLY",
            "payment_mode": "DEVELOPMENT_MANUAL",
            "gateway_reference": "TXN-TEST-1001",
        },
    )
    assert activate_resp.status_code == 200, activate_resp.text
    sub_data = activate_resp.json()
    assert sub_data["status"] == "ACTIVE"


# -----------------------------------------------------------------------------
# 2. Org Admin Login, Branch & Staff Creation with Entitlement Limit Checks
# -----------------------------------------------------------------------------
def test_org_admin_staff_and_entitlement_limits(client: TestClient, db_session: Session) -> None:
    # Setup test Org with a tight plan (max 1 branch, 1 doctor, 1 receptionist)
    plan = SubscriptionPlan(
        name="Strict Tier",
        code="STRICT-01",
        monthly_price=Decimal("999.00"),
        annual_price=Decimal("9990.00"),
        max_doctors=1,
        max_receptionists=1,
        max_branches=1,
        monthly_consultation_limit=50,
        audio_storage_mb_limit=200,
        report_generation_limit=50,
        is_active=True,
    )
    db_session.add(plan)
    db_session.flush()

    org = Organization(
        name="City Health Clinic",
        org_type="CLINIC",
        contact_email="contact@cityhealth.in",
        contact_phone="+919800011122",
        status=OrgStatus.ACTIVE,
    )
    db_session.add(org)
    db_session.flush()

    # Create Initial Branch (which fulfills the 1 max_branch quota)
    loc = OrganizationLocation(
        organization_id=org.id,
        name="City Health Branch 1",
        branch_code="CH-01",
        is_active=True,
    )
    db_session.add(loc)
    db_session.flush()

    # Active subscription
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    sub = Subscription(
        organization_id=org.id,
        plan_id=plan.id,
        status=SubscriptionStatus.ACTIVE,
        billing_cycle=BillingCycle.MONTHLY,
        start_date=now,
        end_date=now + timedelta(days=30),
    )
    db_session.add(sub)
    db_session.flush()

    # Org Admin user
    admin_user = User(
        email="admin@cityhealth.in",
        password_hash=get_password_hash("CityAdmin@123"),
        full_name="City Admin",
        is_super_admin=False,
        is_active=True,
    )
    db_session.add(admin_user)
    db_session.flush()

    db_session.add(
        OrganizationMembership(
            user_id=admin_user.id,
            organization_id=org.id,
            location_id=loc.id,
            role=UserRole.ORG_ADMIN,
            is_active=True,
        )
    )
    db_session.commit()

    # Login as Org Admin
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@cityhealth.in", "password": "CityAdmin@123"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify Dashboard
    dash_resp = client.get("/api/v1/org/dashboard", headers=headers)
    assert dash_resp.status_code == 200
    dash_data = dash_resp.json()
    assert dash_data["organization"]["name"] == "City Health Clinic"
    assert dash_data["branches_count"] == 1

    # Attempt to create a 2nd branch -> MUST FAIL WITH 403 (max_branches=1 reached)
    branch2_resp = client.post(
        "/api/v1/org/branches",
        headers=headers,
        json={"name": "City Health Branch 2", "branch_code": "CH-02"},
    )
    assert branch2_resp.status_code == 403
    assert "branch limit reached" in branch2_resp.json()["detail"].lower()

    # Create 1st Doctor -> SUCCESS (max_doctors=1)
    doc1_resp = client.post(
        "/api/v1/org/staff/doctors",
        headers=headers,
        json={
            "email": "dr.rao@cityhealth.in",
            "password": "Password@123",
            "full_name": "Dr. K. Rao",
            "location_id": str(loc.id),
            "specialization": "Pediatrics",
            "qualification": "MBBS, DCH",
            "registration_number": "REG-PED-101",
        },
    )
    assert doc1_resp.status_code == 201, doc1_resp.text

    # Attempt to create 2nd Doctor -> MUST FAIL WITH 403 (max_doctors=1 reached)
    doc2_resp = client.post(
        "/api/v1/org/staff/doctors",
        headers=headers,
        json={
            "email": "dr.patil@cityhealth.in",
            "password": "Password@123",
            "full_name": "Dr. Patil",
            "location_id": str(loc.id),
            "specialization": "Dermatology",
            "qualification": "MBBS, MD",
            "registration_number": "REG-DERM-102",
        },
    )
    assert doc2_resp.status_code == 403
    assert "doctor limit reached" in doc2_resp.json()["detail"].lower()


# -----------------------------------------------------------------------------
# 3. Cross-Tenant & Role-Based Access Isolation
# -----------------------------------------------------------------------------
def test_cross_tenant_and_rbac_isolation(client: TestClient, db_session: Session) -> None:
    # Org A
    org_a = Organization(
        name="Org Alpha",
        org_type="CLINIC",
        contact_email="a@alpha.in",
        contact_phone="+919111111111",
        status=OrgStatus.ACTIVE,
    )
    db_session.add(org_a)
    db_session.flush()

    # Org B
    org_b = Organization(
        name="Org Beta",
        org_type="CLINIC",
        contact_email="b@beta.in",
        contact_phone="+919222222222",
        status=OrgStatus.ACTIVE,
    )
    db_session.add(org_b)
    db_session.flush()

    # Org Admin A
    admin_a = User(
        email="admin@alpha.in",
        password_hash=get_password_hash("AlphaAdmin@123"),
        full_name="Alpha Admin",
        is_super_admin=False,
        is_active=True,
    )
    db_session.add(admin_a)
    db_session.flush()
    db_session.add(
        OrganizationMembership(
            user_id=admin_a.id,
            organization_id=org_a.id,
            role=UserRole.ORG_ADMIN,
            is_active=True,
        )
    )

    # Doctor in Org A
    doc_a = User(
        email="doctor@alpha.in",
        password_hash=get_password_hash("DoctorAlpha@123"),
        full_name="Doctor Alpha",
        is_super_admin=False,
        is_active=True,
    )
    db_session.add(doc_a)
    db_session.flush()
    db_session.add(
        OrganizationMembership(
            user_id=doc_a.id,
            organization_id=org_a.id,
            role=UserRole.DOCTOR,
            is_active=True,
        )
    )

    db_session.commit()

    # 1. Login as Org A Admin
    login_a = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@alpha.in", "password": "AlphaAdmin@123"},
    )
    token_a = login_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Org A admin attempting to access platform-admin endpoint -> MUST FAIL WITH 403
    platform_resp = client.get("/api/v1/platform/overview", headers=headers_a)
    assert platform_resp.status_code == 403

    # 2. Login as Doctor in Org A
    login_doc = client.post(
        "/api/v1/auth/login",
        json={"email": "doctor@alpha.in", "password": "DoctorAlpha@123"},
    )
    token_doc = login_doc.json()["access_token"]
    headers_doc = {"Authorization": f"Bearer {token_doc}"}

    # Doctor attempting to access Org Admin dashboard or add staff -> MUST FAIL WITH 403
    staff_resp = client.get("/api/v1/org/dashboard", headers=headers_doc)
    assert staff_resp.status_code == 403


# -----------------------------------------------------------------------------
# 4. Complete B2B Customer Onboarding Pipeline -> Owner Alert -> Approval -> Quotas
# -----------------------------------------------------------------------------
def test_b2b_customer_registration_owner_alert_approval_and_quota_enforcement(
    client: TestClient, db_session: Session
) -> None:
    # 0. Setup Platform Owner & a Starter Plan (limit: 2 doctors)
    owner = User(
        email="superadmin.test@arogyascribe.in",
        password_hash=get_password_hash("SuperSecureAdmin@123"),
        full_name="Platform Owner",
        is_super_admin=True,
        is_active=True,
    )
    db_session.add(owner)

    starter_plan = SubscriptionPlan(
        name="Starter Clinic Tier",
        code="STARTER_TIER",
        monthly_price=Decimal("4999.00"),
        annual_price=Decimal("49990.00"),
        max_doctors=2,
        max_receptionists=1,
        max_branches=1,
        monthly_consultation_limit=250,
        audio_storage_mb_limit=25600,
        is_active=True,
    )
    db_session.add(starter_plan)
    db_session.commit()

    # Step 1: Customer submits clinic registration on landing page
    reg_payload = {
        "name": "Apollo Clinic Indiranagar",
        "org_type": "CLINIC",
        "contact_email": "admin@apolloclinic.in",
        "contact_phone": "+919888877777",
        "address": "Indiranagar 100ft Road, Bengaluru",
        "admin_full_name": "Dr. Prathap Reddy",
        "requested_plan": "STARTER_TIER",
        "requested_billing_cycle": "MONTHLY",
        "coupon_code": "WELCOME20",
    }
    reg_resp = client.post("/api/v1/organizations/register", json=reg_payload)
    assert reg_resp.status_code == 201, reg_resp.text
    org_data = reg_resp.json()
    org_id = org_data["id"]
    assert org_data["status"] == "PENDING"
    assert org_data["settings_json"]["requested_plan"] == "STARTER_TIER"

    # Step 2: Unapproved clinic admin cannot log in yet
    unapproved_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@apolloclinic.in", "password": "AnyRandomPassword@123"},
    )
    assert unapproved_login.status_code in (401, 404)

    # Step 3: Platform Owner logs in and connects & approves the organization
    owner_login = client.post(
        "/api/v1/auth/login",
        json={"email": "superadmin.test@arogyascribe.in", "password": "SuperSecureAdmin@123"},
    )
    assert owner_login.status_code == 200
    owner_token = owner_login.json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    approval_payload = {
        "plan_id": str(starter_plan.id),
        "billing_cycle": "MONTHLY",
        "duration_days": 30,
        "admin_email": "admin@apolloclinic.in",
        "admin_full_name": "Dr. Prathap Reddy",
        "temporary_password": "TempClinicPass@123",
    }
    approve_resp = client.post(
        f"/api/v1/platform/organizations/{org_id}/approve-onboarding",
        headers=owner_headers,
        json=approval_payload,
    )
    assert approve_resp.status_code == 200, approve_resp.text
    approval_data = approve_resp.json()
    assert approval_data["status"] == "ACTIVE"
    assert approval_data["temporary_password"] == "TempClinicPass@123"

    # Step 4: Newly approved Org Admin logs in with temporary password
    clinic_admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@apolloclinic.in", "password": "TempClinicPass@123"},
    )
    assert clinic_admin_login.status_code == 200, clinic_admin_login.text
    clinic_admin_token = clinic_admin_login.json()["access_token"]
    clinic_headers = {"Authorization": f"Bearer {clinic_admin_token}"}

    # Step 5: Quota enforcement: Add doctors up to limit (2 doctors max)
    # Doctor 1
    doc1_resp = client.post(
        "/api/v1/org/staff/doctors",
        headers=clinic_headers,
        json={
            "full_name": "Dr. Priya Ramesh",
            "email": "dr.priya@apolloclinic.in",
            "password": "DoctorPass@123",
            "specialization": "Cardiology",
            "qualification": "MBBS, MD",
            "registration_number": "KMC-DOC-001",
        },
    )
    assert doc1_resp.status_code == 201, doc1_resp.text

    # Doctor 2
    doc2_resp = client.post(
        "/api/v1/org/staff/doctors",
        headers=clinic_headers,
        json={
            "full_name": "Dr. Sameer Khan",
            "email": "dr.sameer@apolloclinic.in",
            "password": "DoctorPass@123",
            "specialization": "Pediatrics",
            "qualification": "MBBS, DCH",
            "registration_number": "KMC-DOC-002",
        },
    )
    assert doc2_resp.status_code == 201, doc2_resp.text

    # Doctor 3 (Exceeds Starter quota of 2 doctors) -> MUST FAIL WITH 403
    doc3_resp = client.post(
        "/api/v1/org/staff/doctors",
        headers=clinic_headers,
        json={
            "full_name": "Dr. Rahul Verma",
            "email": "dr.rahul@apolloclinic.in",
            "password": "DoctorPass@123",
            "specialization": "Neurology",
            "qualification": "MBBS, DM",
            "registration_number": "KMC-DOC-003",
        },
    )
    assert doc3_resp.status_code == 403
    assert "limit reached" in doc3_resp.json()["detail"].lower()


