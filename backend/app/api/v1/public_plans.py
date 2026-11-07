from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.subscriptions import DiscountCoupon, SubscriptionPlan
from app.schemas.subscriptions import PlanResponse, ValidateCouponRequest, ValidateCouponResponse

router = APIRouter(tags=["Public Plans"])


@router.get("/plans/public", response_model=list[PlanResponse])
@router.get("/plans", response_model=list[PlanResponse])
def get_public_subscription_plans(
    db: Annotated[Session, Depends(get_db)],
) -> list[SubscriptionPlan]:
    """Public endpoint to fetch active subscription plans for landing page and registration."""
    return list(
        db.execute(
            select(SubscriptionPlan)
            .where(SubscriptionPlan.is_active.is_(True))
            .order_by(SubscriptionPlan.monthly_price.asc())
        ).scalars().all()
    )


@router.post("/plans/validate-coupon", response_model=ValidateCouponResponse)
def validate_coupon(
    data: ValidateCouponRequest,
    db: Annotated[Session, Depends(get_db)],
) -> ValidateCouponResponse:
    """Validate a discount coupon against a specific subscription tier."""
    clean_code = data.coupon_code.upper().strip()
    coupon = db.execute(
        select(DiscountCoupon).where(DiscountCoupon.code == clean_code, DiscountCoupon.is_active.is_(True))
    ).scalar_one_or_none()

    if not coupon:
        return ValidateCouponResponse(
            valid=False,
            coupon_code=clean_code,
            message="Invalid coupon code.",
        )

    if coupon.valid_until and coupon.valid_until < datetime.now(timezone.utc):
        return ValidateCouponResponse(
            valid=False,
            coupon_code=clean_code,
            message="This coupon has expired.",
        )

    if coupon.current_redemptions >= coupon.max_redemptions:
        return ValidateCouponResponse(
            valid=False,
            coupon_code=clean_code,
            message="This coupon has reached its maximum redemptions limit.",
        )

    # Check Plan
    clean_plan_code = data.plan_code.upper().strip()
    plan = db.execute(
        select(SubscriptionPlan).where(SubscriptionPlan.code == clean_plan_code)
    ).scalar_one_or_none()

    if not plan:
        return ValidateCouponResponse(
            valid=False,
            coupon_code=clean_code,
            message=f"Plan '{clean_plan_code}' not found.",
        )

    # Check applicability
    if coupon.applicable_plan_codes and clean_plan_code not in [c.upper() for c in coupon.applicable_plan_codes]:
        return ValidateCouponResponse(
            valid=False,
            coupon_code=clean_code,
            message=f"Coupon only applies to {', '.join(coupon.applicable_plan_codes)} plans.",
        )

    # Compute discounts
    if coupon.discount_type == "PERCENTAGE":
        pct = coupon.discount_value / Decimal("100")
        disc_monthly = round(plan.monthly_price * pct, 2)
        disc_annual = round(plan.annual_price * pct, 2)
    else:  # FLAT_INR
        disc_monthly = min(coupon.discount_value, plan.monthly_price)
        disc_annual = min(coupon.discount_value, plan.annual_price)

    final_monthly = max(Decimal("0.00"), plan.monthly_price - disc_monthly)
    final_annual = max(Decimal("0.00"), plan.annual_price - disc_annual)

    return ValidateCouponResponse(
        valid=True,
        coupon_code=coupon.code,
        discount_type=coupon.discount_type,
        discount_value=coupon.discount_value,
        discount_amount_monthly=disc_monthly,
        discount_amount_annual=disc_annual,
        final_price_monthly=final_monthly,
        final_price_annual=final_annual,
        message=f"Coupon '{coupon.code}' successfully applied!",
    )


