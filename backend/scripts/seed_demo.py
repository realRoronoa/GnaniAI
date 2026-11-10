"""Synthetic Demo Data Seeder for ArogyaScribe

Idempotently provisions:
- Super Admin / Platform Owner
- 3 Subscription Plans (Starter, Professional, Enterprise)
- Demo Healthcare Organization with 2 Branches and an Active Professional Subscription
- Org Admin, Receptionist, and Doctor profiles with weekly consultation schedules
- 2 Synthetic Patients with sample outpatient appointments
"""
import os
import sys
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any
import uuid

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.enums import (
    AppointmentStatus,
    AppointmentType,
    BillingCycle,
    OrgStatus,
    PaymentMode,
    PaymentStatus,
    SubscriptionStatus,
    UserRole,
)
from app.models.patients_appointments import Appointment, DoctorSchedule, Patient
from app.models.subscriptions import (
    DiscountCoupon,
    PaymentTransaction,
    Subscription,
    SubscriptionPlan,
    UsageRecord,
)
from app.models.tenant import (
    DoctorProfile,
    Organization,
    OrganizationLocation,
    OrganizationMembership,
    ReceptionistProfile,
    User,
)


def wipe_all_tenant_data(db_session: Session | None = None) -> dict[str, Any]:
    """Completely clears all organizations, locations, doctors, receptionists,
    patients, appointments, consultations, transcripts, facts, medications,
    and reports from the database.
    Strictly preserves SuperAdmin and SubscriptionPlans.
    """
    close_after = False
    if db_session is None:
        db = SessionLocal()
        close_after = True
    else:
        db = db_session

    try:
        from sqlalchemy import delete
        from app.models.clinical_reports import (
            ClinicalFact,
            ClinicalFactEvidence,
            MedicationInstruction,
            PdfAsset,
            Report,
            ReportApproval,
            ReportVersion,
        )
        from app.models.consultations_audio import (
            AudioAsset,
            ConsentRecord,
            Consultation,
            TranscriptSegment,
            TranscriptVersion,
        )
        from app.models.patients_appointments import (
            Appointment,
            DoctorSchedule,
            Patient,
        )
        from app.models.subscriptions import (
            PaymentTransaction,
            Subscription,
            UsageRecord,
        )
        from app.models.system_audit import (
            AuditEvent,
            ProcessingJob,
            SecureShareGrant,
        )
        from app.models.tenant import (
            DoctorProfile,
            Organization,
            OrganizationLocation,
            OrganizationMembership,
            ReceptionistProfile,
            User,
        )

        # 1. Audit and Share Grants
        db.execute(delete(SecureShareGrant))
        db.execute(delete(AuditEvent))
        db.execute(delete(ProcessingJob))

        # 2. Reports and Clinical Evidence
        db.execute(delete(PdfAsset))
        db.execute(delete(ReportApproval))
        db.execute(delete(ReportVersion))
        db.execute(delete(Report))
        db.execute(delete(MedicationInstruction))
        db.execute(delete(ClinicalFactEvidence))
        db.execute(delete(ClinicalFact))

        # 3. Transcripts & Audio
        db.execute(delete(TranscriptSegment))
        db.execute(delete(TranscriptVersion))
        db.execute(delete(AudioAsset))
        db.execute(delete(ConsentRecord))

        # 4. Consultations & Appointments
        db.execute(delete(Consultation))
        db.execute(delete(Appointment))
        db.execute(delete(DoctorSchedule))
        db.execute(delete(Patient))

        # 5. Profiles & Memberships
        db.execute(delete(DoctorProfile))
        db.execute(delete(ReceptionistProfile))
        db.execute(delete(OrganizationMembership))

        # 6. Usage & Subscriptions
        db.execute(delete(UsageRecord))
        db.execute(delete(PaymentTransaction))
        db.execute(delete(Subscription))

        # 7. Locations & Organizations
        db.execute(delete(OrganizationLocation))
        db.execute(delete(Organization))

        # 8. All non-superadmin Users
        db.execute(delete(User).where(User.is_super_admin == False))

        db.commit()

        # Re-ensure SuperAdmin and Subscription Plans are present
        seed_essentials(target_engine=db.get_bind(), target_session_factory=lambda: db)

        print("[WIPE] Database wiped 100% clean of all tenant data. SuperAdmin & Plans intact.")
        return {"status": "success", "message": "All tenant data wiped clean. Ready for fresh doctor and clinic onboarding."}
    finally:
        if close_after:
            db.close()


def clean_mock_data(db_session: Session | None = None) -> dict[str, int]:
    """Removes all pre-seeded mock clinic records from the database while strictly preserving Super Admin and Plans."""
    close_after = False
    if db_session is None:
        db = SessionLocal()
        close_after = True
    else:
        db = db_session

    try:
        demo_orgs = db.execute(
            select(Organization).where(Organization.name.ilike("%Arogya Care%"))
        ).scalars().all()
        org_count = len(demo_orgs)
        for org in demo_orgs:
            db.delete(org)

        demo_emails = [
            "orgadmin@arogyacare.in",
            "reception@arogyacare.in",
            "dr.sharma@arogyacare.in",
        ]
        demo_users = db.execute(
            select(User).where(User.email.in_(demo_emails))
        ).scalars().all()
        user_count = len(demo_users)
        for u in demo_users:
            db.delete(u)

        db.commit()
        print(f"[CLEANUP] Removed {org_count} demo organization(s) and {user_count} demo user(s). Database is clean!")
        return {"organizations_removed": org_count, "users_removed": user_count}
    finally:
        if close_after:
            db.close()


def seed_essentials(target_engine=None, target_session_factory=None) -> None:
    """Provisions ONLY the Super Admin, the 3 Subscription Plans, and Discount Coupons.
    Does NOT seed any mock clinics, doctors, receptionists, or patients.
    """
    t_engine = target_engine or engine
    t_session = target_session_factory or SessionLocal

    Base.metadata.create_all(bind=t_engine)

    with t_session() as db:
        # 1. Super Admin
        superadmin_email = getattr(settings, "SUPERADMIN_EMAIL", "superadmin@arogyascribe.in")
        superadmin_password = getattr(settings, "SUPERADMIN_INITIAL_PASSWORD", "Admin@12345")
        superadmin = db.execute(select(User).where(User.email == superadmin_email)).scalar_one_or_none()
        if not superadmin:
            superadmin = User(
                email=superadmin_email,
                password_hash=get_password_hash(superadmin_password),
                full_name="Platform Super Administrator",
                phone="+919999900000",
                is_super_admin=True,
                is_active=True,
            )
            db.add(superadmin)
            db.flush()
            print(f"Created Platform Owner: {superadmin_email}")
        else:
            superadmin.password_hash = get_password_hash(superadmin_password)

        # 2. Subscription Plans
        plans_data = [
            {
                "code": "STARTER",
                "name": "Starter",
                "description": "For independent clinics.",
                "monthly_price": Decimal("4999.00"),
                "annual_price": Decimal("49990.00"),
                "max_doctors": 2,
                "max_receptionists": 1,
                "max_branches": 1,
                "monthly_consultation_limit": 250,
                "audio_storage_mb_limit": 25600,
                "report_generation_limit": 250,
                "included_features_json": [
                    "Up to 2 doctors",
                    "1 receptionist",
                    "250 consultations/month",
                    "25 GB private storage",
                    "Reception queue and appointments",
                    "Consent-first recording",
                    "Doctor report and patient summary PDFs",
                ],
                "duration_days": 30,
                "trial_days": 14,
                "is_active": True,
            },
            {
                "code": "PROFESSIONAL",
                "name": "Professional",
                "description": "For growing clinics.",
                "monthly_price": Decimal("14999.00"),
                "annual_price": Decimal("149990.00"),
                "max_doctors": 10,
                "max_receptionists": 4,
                "max_branches": 3,
                "monthly_consultation_limit": 1000,
                "audio_storage_mb_limit": 102400,
                "report_generation_limit": 1000,
                "included_features_json": [
                    "Up to 10 doctors",
                    "4 receptionists",
                    "1,000 consultations/month",
                    "100 GB private storage",
                    "Multiple clinic locations",
                    "Hindi patient summaries",
                    "Staff and appointment management",
                    "Extended audit history",
                ],
                "duration_days": 30,
                "trial_days": 14,
                "is_active": True,
            },
            {
                "code": "ENTERPRISE",
                "name": "Enterprise",
                "description": "For hospitals and medical centres.",
                "monthly_price": Decimal("49999.00"),
                "annual_price": Decimal("499990.00"),
                "max_doctors": 25,
                "max_receptionists": 10,
                "max_branches": 10,
                "monthly_consultation_limit": 3000,
                "audio_storage_mb_limit": 512000,
                "report_generation_limit": 3000,
                "included_features_json": [
                    "Up to 25 doctors",
                    "10 receptionists",
                    "3,000 consultations/month",
                    "500 GB private storage",
                    "Multiple branches",
                    "Advanced audit logs",
                    "Priority support",
                    "Centralized organization management",
                ],
                "duration_days": 30,
                "trial_days": 14,
                "is_active": True,
            },
        ]
        for p in plans_data:
            existing_plan = db.execute(
                select(SubscriptionPlan).where(SubscriptionPlan.code == p["code"])
            ).scalar_one_or_none()
            if not existing_plan:
                plan_obj = SubscriptionPlan(**p)
                db.add(plan_obj)
            else:
                for k, v in p.items():
                    setattr(existing_plan, k, v)

        # 3. Discount Coupons
        coupons_data = [
            {
                "code": "WELCOME20",
                "description": "20% Inaugural Clinic Discount",
                "discount_type": "PERCENTAGE",
                "discount_value": Decimal("20.00"),
                "applicable_plan_codes": ["STARTER", "PROFESSIONAL", "ENTERPRISE"],
                "max_redemptions": 500,
                "current_redemptions": 12,
                "is_active": True,
            },
            {
                "code": "CLINIC2000",
                "description": "Flat ₹2,000 Off Independent Clinics",
                "discount_type": "FLAT_INR",
                "discount_value": Decimal("2000.00"),
                "applicable_plan_codes": ["STARTER", "PROFESSIONAL"],
                "max_redemptions": 200,
                "current_redemptions": 5,
                "is_active": True,
            },
        ]
        for c in coupons_data:
            existing_c = db.execute(select(DiscountCoupon).where(DiscountCoupon.code == c["code"])).scalar_one_or_none()
            if not existing_c:
                db.add(DiscountCoupon(**c))
            else:
                for k, v in c.items():
                    setattr(existing_c, k, v)

        db.commit()
        print("[ESSENTIALS] Super Admin, 3 Plans, and Coupons verified successfully!")


def seed(custom_db_url: str | None = None) -> None:
    print("=" * 60)
    print("Seeding Synthetic Demo Data for ArogyaScribe...")
    print("=" * 60)

    # Determine target engine
    target_engine = engine
    target_session_factory = SessionLocal

    if custom_db_url or "--sqlite" in sys.argv:
        db_url = custom_db_url or "sqlite:///demo.db"
        print(f"Using local SQLite database: {db_url}")
        target_engine = create_engine(db_url, connect_args={"check_same_thread": False})
        target_session_factory = sessionmaker(autocommit=False, autoflush=False, bind=target_engine)
    else:
        try:
            with target_engine.connect():
                pass
        except Exception:
            print("[NOTICE] PostgreSQL not reachable on localhost:5432. Falling back to local SQLite: sqlite:///demo.db")
            target_engine = create_engine("sqlite:///demo.db", connect_args={"check_same_thread": False})
            target_session_factory = sessionmaker(autocommit=False, autoflush=False, bind=target_engine)

    # Ensure tables exist
    Base.metadata.create_all(bind=target_engine)

    with target_session_factory() as db:
        now = datetime.now(timezone.utc)
        today = date.today()

        # ---------------------------------------------------------------------
        # 1. Platform Owner / Super Admin
        # ---------------------------------------------------------------------
        superadmin_email = getattr(settings, "SUPERADMIN_EMAIL", "superadmin@arogyascribe.in")
        superadmin_password = getattr(settings, "SUPERADMIN_INITIAL_PASSWORD", "Admin@12345")
        superadmin = db.execute(select(User).where(User.email == superadmin_email)).scalar_one_or_none()
        if not superadmin:
            superadmin = User(
                email=superadmin_email,
                password_hash=get_password_hash(superadmin_password),
                full_name="Platform Super Administrator",
                phone="+919999900000",
                is_super_admin=True,
                is_active=True,
            )
            db.add(superadmin)
            db.flush()
            print(f"Created Platform Owner: {superadmin_email}")
        else:
            superadmin.password_hash = get_password_hash(superadmin_password)
            db.flush()
            print(f"Platform Owner verified: {superadmin_email}")

        # Ensure description column exists in subscription_plans
        try:
            from sqlalchemy import text
            with target_engine.connect() as conn:
                conn.execute(text("ALTER TABLE subscription_plans ADD COLUMN description VARCHAR(255)"))
                conn.commit()
        except Exception:
            pass

        # ---------------------------------------------------------------------
        # 2. Subscription Plans
        # ---------------------------------------------------------------------
        plans_data = [
            {
                "code": "STARTER",
                "name": "Starter",
                "description": "For independent clinics.",
                "monthly_price": Decimal("4999.00"),
                "annual_price": Decimal("49990.00"),
                "max_doctors": 2,
                "max_receptionists": 1,
                "max_branches": 1,
                "monthly_consultation_limit": 250,
                "audio_storage_mb_limit": 25600,  # 25 GB
                "report_generation_limit": 250,
                "included_features_json": [
                    "Up to 2 doctors",
                    "1 receptionist",
                    "250 consultations/month",
                    "25 GB private storage",
                    "Reception queue and appointments",
                    "Consent-first recording",
                    "Doctor report and patient summary PDFs",
                ],
                "duration_days": 30,
                "trial_days": 14,
                "is_active": True,
            },
            {
                "code": "PROFESSIONAL",
                "name": "Professional",
                "description": "For growing clinics.",
                "monthly_price": Decimal("14999.00"),
                "annual_price": Decimal("149990.00"),
                "max_doctors": 10,
                "max_receptionists": 4,
                "max_branches": 3,
                "monthly_consultation_limit": 1000,
                "audio_storage_mb_limit": 102400,  # 100 GB
                "report_generation_limit": 1000,
                "included_features_json": [
                    "Up to 10 doctors",
                    "4 receptionists",
                    "1,000 consultations/month",
                    "100 GB private storage",
                    "Multiple clinic locations",
                    "Hindi patient summaries",
                    "Staff and appointment management",
                    "Extended audit history",
                ],
                "duration_days": 30,
                "trial_days": 14,
                "is_active": True,
            },
            {
                "code": "ENTERPRISE",
                "name": "Enterprise",
                "description": "For hospitals and medical centres.",
                "monthly_price": Decimal("49999.00"),
                "annual_price": Decimal("499990.00"),
                "max_doctors": 25,
                "max_receptionists": 10,
                "max_branches": 10,
                "monthly_consultation_limit": 3000,
                "audio_storage_mb_limit": 512000,  # 500 GB
                "report_generation_limit": 3000,
                "included_features_json": [
                    "Up to 25 doctors",
                    "10 receptionists",
                    "3,000 consultations/month",
                    "500 GB private storage",
                    "Multiple branches",
                    "Advanced audit logs",
                    "Priority support",
                    "Centralized organization management",
                ],
                "duration_days": 30,
                "trial_days": 14,
                "is_active": True,
            },
        ]

        plans: dict[str, SubscriptionPlan] = {}
        for p in plans_data:
            existing_plan = db.execute(
                select(SubscriptionPlan).where(SubscriptionPlan.code == p["code"])
            ).scalar_one_or_none()
            if not existing_plan:
                plan_obj = SubscriptionPlan(**p)
                db.add(plan_obj)
                db.flush()
                plans[p["code"]] = plan_obj
                print(f"Created Plan: {p['name']} ({p['code']})")
            else:
                for k, v in p.items():
                    setattr(existing_plan, k, v)
                db.flush()
                plans[p["code"]] = existing_plan
                print(f"Updated Plan: {p['name']} ({p['code']})")

        # ---------------------------------------------------------------------
        # 2b. Discount Coupons (Super Admin Managed)
        # ---------------------------------------------------------------------
        coupons_data = [
            {
                "code": "WELCOME20",
                "description": "20% Inaugural Clinic Discount",
                "discount_type": "PERCENTAGE",
                "discount_value": Decimal("20.00"),
                "applicable_plan_codes": ["STARTER", "PROFESSIONAL", "ENTERPRISE"],
                "max_redemptions": 500,
                "current_redemptions": 12,
                "is_active": True,
            },
            {
                "code": "CLINIC2000",
                "description": "Flat ₹2,000 Off Independent Clinics",
                "discount_type": "FLAT_INR",
                "discount_value": Decimal("2000.00"),
                "applicable_plan_codes": ["STARTER", "PROFESSIONAL"],
                "max_redemptions": 200,
                "current_redemptions": 5,
                "is_active": True,
            },
            {
                "code": "SPECIAL999",
                "description": "Flat ₹999 Launch Special",
                "discount_type": "FLAT_INR",
                "discount_value": Decimal("999.00"),
                "applicable_plan_codes": ["STARTER", "PROFESSIONAL", "ENTERPRISE"],
                "max_redemptions": 1000,
                "current_redemptions": 24,
                "is_active": True,
            },
        ]
        for c in coupons_data:
            existing_c = db.execute(select(DiscountCoupon).where(DiscountCoupon.code == c["code"])).scalar_one_or_none()
            if not existing_c:
                c_obj = DiscountCoupon(**c)
                db.add(c_obj)
                db.flush()
                print(f"Created Coupon: {c['code']}")
            else:
                for k, v in c.items():
                    setattr(existing_c, k, v)
                db.flush()
                print(f"Updated Coupon: {c['code']}")


        # ---------------------------------------------------------------------
        # 3. Demo Organization
        # ---------------------------------------------------------------------
        demo_org_name = "Arogya Care Multi-Specialty Clinic (Bengaluru)"
        demo_org = db.execute(
            select(Organization).where(Organization.name == demo_org_name)
        ).scalar_one_or_none()

        if not demo_org:
            demo_org = Organization(
                name=demo_org_name,
                org_type="POLYCLINIC",
                contact_email="contact@arogyacare.in",
                contact_phone="+919876543210",
                address="100 Feet Road, Indiranagar, Bengaluru, Karnataka 560038",
                registration_number="KA-MED-2022-0941",
                status=OrgStatus.ACTIVE,
                settings_json={
                    "timezone": "Asia/Kolkata",
                    "default_language": "hi-IN",
                    "supported_languages": ["en-IN", "hi-IN", "kn-IN"],
                },
            )
            db.add(demo_org)
            db.flush()
            print(f"Created Organization: {demo_org.name}")
        else:
            print(f"Organization already exists: {demo_org.name}")

        # ---------------------------------------------------------------------
        # 4. Organization Locations (Branches)
        # ---------------------------------------------------------------------
        branches_data = [
            {
                "organization_id": demo_org.id,
                "name": "Indiranagar Main Branch",
                "branch_code": "BLR-IND-01",
                "address": "100 Feet Road, Indiranagar, Bengaluru, Karnataka 560038",
                "phone": "+919876543211",
                "is_active": True,
            },
            {
                "organization_id": demo_org.id,
                "name": "Koramangala Branch",
                "branch_code": "BLR-KOR-02",
                "address": "80 Feet Road, Koramangala 4th Block, Bengaluru, Karnataka 560034",
                "phone": "+919876543212",
                "is_active": True,
            },
        ]

        branches: dict[str, OrganizationLocation] = {}
        for b in branches_data:
            existing_branch = db.execute(
                select(OrganizationLocation).where(
                    OrganizationLocation.organization_id == demo_org.id,
                    OrganizationLocation.branch_code == b["branch_code"],
                )
            ).scalar_one_or_none()
            if not existing_branch:
                branch_obj = OrganizationLocation(**b)
                db.add(branch_obj)
                db.flush()
                branches[b["branch_code"]] = branch_obj
                print(f"Created Branch: {b['name']} ({b['branch_code']})")
            else:
                branches[b["branch_code"]] = existing_branch
                print(f"Branch already exists: {b['branch_code']}")

        main_branch = branches["BLR-IND-01"]

        # ---------------------------------------------------------------------
        # 5. Subscription for Demo Organization
        # ---------------------------------------------------------------------
        existing_sub = db.execute(
            select(Subscription).where(Subscription.organization_id == demo_org.id)
        ).scalar_one_or_none()

        if not existing_sub:
            pro_plan = plans["PROFESSIONAL"]
            subscription = Subscription(
                organization_id=demo_org.id,
                plan_id=pro_plan.id,
                status=SubscriptionStatus.ACTIVE,
                billing_cycle=BillingCycle.MONTHLY,
                start_date=now,
                end_date=now + timedelta(days=30),
                auto_renew=True,
                activated_by_user_id=superadmin.id,
            )
            db.add(subscription)
            db.flush()

            # Record payment transaction
            payment = PaymentTransaction(
                organization_id=demo_org.id,
                subscription_id=subscription.id,
                amount=pro_plan.monthly_price,
                currency="INR",
                payment_mode=PaymentMode.DEVELOPMENT_MANUAL,
                gateway_reference="DEMO-PAY-INITIAL-001",
                status=PaymentStatus.VERIFIED,
                verified_at=now,
            )
            db.add(payment)

            # Record initial usage
            usage = UsageRecord(
                organization_id=demo_org.id,
                subscription_id=subscription.id,
                period_month=now.strftime("%Y-%m"),
                consultations_count=0,
                audio_storage_bytes_used=0,
                reports_generated_count=0,
                active_doctors_count=1,
                active_receptionists_count=1,
                active_branches_count=2,
            )
            db.add(usage)
            db.flush()
            print(f"Created Subscription (Professional Plan) for {demo_org.name}")
        else:
            print("Subscription already active for organization.")

        # ---------------------------------------------------------------------
        # 6. Users: Org Admin, Receptionist, Doctor
        # ---------------------------------------------------------------------
        demo_org_admin_pass = getattr(settings, "DEMO_ORG_ADMIN_PASSWORD", "OrgAdmin@123")
        demo_receptionist_pass = getattr(settings, "DEMO_RECEPTIONIST_PASSWORD", "Reception@123")
        demo_doctor_pass = getattr(settings, "DEMO_DOCTOR_PASSWORD", "Doctor@123")

        # Org Admin
        admin_email = "orgadmin@arogyacare.in"
        org_admin = db.execute(select(User).where(User.email == admin_email)).scalar_one_or_none()
        if not org_admin:
            org_admin = User(
                email=admin_email,
                password_hash=get_password_hash(demo_org_admin_pass),
                full_name="Dr. Rajesh Varma",
                phone="+919876500001",
                is_super_admin=False,
                is_active=True,
            )
            db.add(org_admin)
            db.flush()
            db.add(
                OrganizationMembership(
                    user_id=org_admin.id,
                    organization_id=demo_org.id,
                    location_id=main_branch.id,
                    role=UserRole.ORG_ADMIN,
                    is_active=True,
                )
            )
            print(f"Created Org Admin: {admin_email}")
        else:
            org_admin.password_hash = get_password_hash(demo_org_admin_pass)
            db.flush()
            print(f"Org Admin already exists: {admin_email}")

        # Receptionist
        reception_email = "reception@arogyacare.in"
        receptionist = db.execute(select(User).where(User.email == reception_email)).scalar_one_or_none()
        if not receptionist:
            receptionist = User(
                email=reception_email,
                password_hash=get_password_hash(demo_receptionist_pass),
                full_name="Pooja Sharma",
                phone="+919876500002",
                is_super_admin=False,
                is_active=True,
            )
            db.add(receptionist)
            db.flush()
            db.add(
                OrganizationMembership(
                    user_id=receptionist.id,
                    organization_id=demo_org.id,
                    location_id=main_branch.id,
                    role=UserRole.RECEPTIONIST,
                    is_active=True,
                )
            )
            db.add(
                ReceptionistProfile(
                    user_id=receptionist.id,
                    organization_id=demo_org.id,
                    location_id=main_branch.id,
                    desk_identifier="Front Desk 1",
                    shift_notes="Morning & Afternoon Outpatient Roster",
                )
            )
            print(f"Created Receptionist: {reception_email}")
        else:
            receptionist.password_hash = get_password_hash(demo_receptionist_pass)
            db.flush()
            print(f"Receptionist already exists: {reception_email}")

        # Doctor
        doctor_email = "dr.sharma@arogyacare.in"
        doctor = db.execute(select(User).where(User.email == doctor_email)).scalar_one_or_none()
        if not doctor:
            doctor = User(
                email=doctor_email,
                password_hash=get_password_hash(demo_doctor_pass),
                full_name="Dr. Ananya Sharma",
                phone="+919876500003",
                is_super_admin=False,
                is_active=True,
            )
            db.add(doctor)
            db.flush()
            db.add(
                OrganizationMembership(
                    user_id=doctor.id,
                    organization_id=demo_org.id,
                    location_id=main_branch.id,
                    role=UserRole.DOCTOR,
                    is_active=True,
                )
            )
            db.add(
                DoctorProfile(
                    user_id=doctor.id,
                    organization_id=demo_org.id,
                    location_id=main_branch.id,
                    specialization="General Medicine",
                    qualification="MBBS, MD (Internal Medicine)",
                    registration_number="KMC-2018-98765",
                    consultation_room="Consultation Room 102",
                    languages_spoken="English, Hindi, Kannada",
                )
            )
            # Create doctor schedules (Monday to Saturday: days 0 to 5)
            for day in range(6):
                db.add(
                    DoctorSchedule(
                        organization_id=demo_org.id,
                        location_id=main_branch.id,
                        doctor_user_id=doctor.id,
                        day_of_week=day,
                        start_time=time(9, 0),
                        end_time=time(17, 0),
                        slot_duration_minutes=15,
                        is_active=True,
                    )
                )
            print(f"Created Doctor & Schedules: {doctor_email}")
        else:
            doctor.password_hash = get_password_hash(demo_doctor_pass)
            db.flush()
            print(f"Doctor already exists: {doctor_email}")

        # ---------------------------------------------------------------------
        # 7. Synthetic Patients (Strictly Clinical/Admin - NO PASSWORDS)
        # ---------------------------------------------------------------------
        patient_1_id = "P-2026-0001"
        patient_1 = db.execute(
            select(Patient).where(
                Patient.organization_id == demo_org.id,
                Patient.patient_identifier == patient_1_id,
            )
        ).scalar_one_or_none()

        if not patient_1:
            patient_1 = Patient(
                organization_id=demo_org.id,
                patient_identifier=patient_1_id,
                full_name="Ramesh Kumar",
                date_of_birth=date(1980, 5, 15),
                age_years=46,
                gender="MALE",
                mobile_number="+919811122233",
                email="ramesh.kumar.demo@example.com",
                preferred_language="hi-IN",
                allergies_summary="No known drug allergies (NKDA)",
                allergy_verification_status="VERIFIED",
                administrative_notes="Regular patient for seasonal fever checkups.",
            )
            db.add(patient_1)
            db.flush()
            print(f"Created Patient 1: {patient_1.full_name} ({patient_1_id})")

            # Create sample appointment
            app_1 = Appointment(
                organization_id=demo_org.id,
                location_id=main_branch.id,
                patient_id=patient_1.id,
                doctor_user_id=doctor.id,
                created_by_user_id=receptionist.id,
                appointment_date=today,
                scheduled_time=datetime.combine(today, time(10, 30), tzinfo=timezone.utc),
                queue_position=1,
                appointment_type=AppointmentType.SCHEDULED,
                status=AppointmentStatus.WAITING,
                reason_for_visit="High fever and body ache for 3 days",
                administrative_notes="Patient arrived at 10:15 AM.",
                arrived_at=now - timedelta(minutes=15),
            )
            db.add(app_1)
        else:
            print(f"Patient 1 already exists: {patient_1_id}")

        patient_2_id = "P-2026-0002"
        patient_2 = db.execute(
            select(Patient).where(
                Patient.organization_id == demo_org.id,
                Patient.patient_identifier == patient_2_id,
            )
        ).scalar_one_or_none()

        if not patient_2:
            patient_2 = Patient(
                organization_id=demo_org.id,
                patient_identifier=patient_2_id,
                full_name="Lakshmi Devi",
                date_of_birth=date(1965, 8, 20),
                age_years=61,
                gender="FEMALE",
                mobile_number="+919844455566",
                email="lakshmi.devi.demo@example.com",
                preferred_language="kn-IN",
                allergies_summary="Penicillin allergy (hives and rash)",
                allergy_verification_status="VERIFIED",
                administrative_notes="Accompanied by daughter. Prefers Kannada dialogue.",
            )
            db.add(patient_2)
            db.flush()
            print(f"Created Patient 2: {patient_2.full_name} ({patient_2_id})")

            # Create sample appointment
            app_2 = Appointment(
                organization_id=demo_org.id,
                location_id=main_branch.id,
                patient_id=patient_2.id,
                doctor_user_id=doctor.id,
                created_by_user_id=receptionist.id,
                appointment_date=today,
                scheduled_time=datetime.combine(today, time(11, 15), tzinfo=timezone.utc),
                queue_position=2,
                appointment_type=AppointmentType.WALK_IN,
                status=AppointmentStatus.SCHEDULED,
                reason_for_visit="Routine hypertension follow-up and prescription refill",
                administrative_notes="Walk-in registered at reception.",
            )
            db.add(app_2)
        else:
            print(f"Patient 2 already exists: {patient_2_id}")

        # ---------------------------------------------------------------------
        # 7b. Multilingual Patients: Tamil & Telugu
        # ---------------------------------------------------------------------
        patient_3_id = "P-2026-0003"
        patient_3 = db.execute(
            select(Patient).where(
                Patient.organization_id == demo_org.id,
                Patient.patient_identifier == patient_3_id,
            )
        ).scalar_one_or_none()

        if not patient_3:
            patient_3 = Patient(
                organization_id=demo_org.id,
                patient_identifier=patient_3_id,
                full_name="Karthik Subramanian",
                date_of_birth=date(1988, 11, 12),
                age_years=38,
                gender="MALE",
                mobile_number="+919444455566",
                email="karthik.subramanian.demo@example.com",
                preferred_language="ta",
                allergies_summary="Sulfa drugs allergy",
                allergy_verification_status="VERIFIED",
                administrative_notes="Prefers consultation summary in Tamil (தமிழ்).",
            )
            db.add(patient_3)
            db.flush()
            print(f"Created Patient 3: {patient_3.full_name} ({patient_3_id} - Tamil)")

            app_3 = Appointment(
                organization_id=demo_org.id,
                location_id=main_branch.id,
                patient_id=patient_3.id,
                doctor_user_id=doctor.id,
                created_by_user_id=receptionist.id,
                appointment_date=today,
                scheduled_time=datetime.combine(today, time(12, 0), tzinfo=timezone.utc),
                queue_position=3,
                appointment_type=AppointmentType.SCHEDULED,
                status=AppointmentStatus.WAITING,
                reason_for_visit="Persistent dry cough and mild chest tightness",
                administrative_notes="Tamil audio recording and vernacular summary requested.",
                arrived_at=now - timedelta(minutes=5),
            )
            db.add(app_3)
        else:
            print(f"Patient 3 already exists: {patient_3_id}")

        patient_4_id = "P-2026-0004"
        patient_4 = db.execute(
            select(Patient).where(
                Patient.organization_id == demo_org.id,
                Patient.patient_identifier == patient_4_id,
            )
        ).scalar_one_or_none()

        if not patient_4:
            patient_4 = Patient(
                organization_id=demo_org.id,
                patient_identifier=patient_4_id,
                full_name="Ananya Reddy",
                date_of_birth=date(1992, 3, 25),
                age_years=34,
                gender="FEMALE",
                mobile_number="+919777788899",
                email="ananya.reddy.demo@example.com",
                preferred_language="te",
                allergies_summary="No known drug allergies (NKDA)",
                allergy_verification_status="VERIFIED",
                administrative_notes="Prefers consultation summary in Telugu (తెలుగు).",
            )
            db.add(patient_4)
            db.flush()
            print(f"Created Patient 4: {patient_4.full_name} ({patient_4_id} - Telugu)")

            app_4 = Appointment(
                organization_id=demo_org.id,
                location_id=main_branch.id,
                patient_id=patient_4.id,
                doctor_user_id=doctor.id,
                created_by_user_id=receptionist.id,
                appointment_date=today,
                scheduled_time=datetime.combine(today, time(12, 30), tzinfo=timezone.utc),
                queue_position=4,
                appointment_type=AppointmentType.WALK_IN,
                status=AppointmentStatus.SCHEDULED,
                reason_for_visit="Migraine headaches with aura and nausea",
                administrative_notes="Telugu patient summary requested.",
            )
            db.add(app_4)
        else:
            print(f"Patient 4 already exists: {patient_4_id}")

        db.commit()

    print("=" * 60)
    print("Synthetic Demo Data Successfully Seeded!")
    print("=" * 60)
    print("DEMO CREDENTIALS:")
    print("1. Platform Owner : superadmin@arogyascribe.in / Admin@12345")
    print("2. Org Admin      : orgadmin@arogyacare.in / OrgAdmin@123")
    print("3. Receptionist   : reception@arogyacare.in / Reception@123")
    print("4. Doctor         : dr.sharma@arogyacare.in / Doctor@123")
    print("=" * 60)


if __name__ == "__main__":
    seed()
