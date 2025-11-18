import hashlib
from datetime import datetime, timedelta
from typing import Any, Final

from django.conf import settings
from django.utils import timezone

from api.models import Buyer

DEFAULT_PAYWALL_PERCENT: Final[int] = 10
DEFAULT_TRIAL_DAYS: Final[int] = 45


def clamp_percentage(raw_percent: int) -> int:
    return max(0, min(100, raw_percent))


def get_paywall_percentage() -> int:
    configured_value: Any = getattr(
        settings,
        "SUBSCRIPTION_PAYWALL_PERCENT",
        DEFAULT_PAYWALL_PERCENT,
    )
    if not isinstance(configured_value, int):
        return DEFAULT_PAYWALL_PERCENT
    return clamp_percentage(configured_value)


def pick_subscription_variant(identifier: str) -> str:
    percent = get_paywall_percentage()
    if percent <= 0:
        return Buyer.OnboardingVariant.TRIAL_FIRST
    if percent >= 100:
        return Buyer.OnboardingVariant.PAYWALL_FIRST
    digest = hashlib.sha256(identifier.encode("utf-8")).digest()
    bucket = int.from_bytes(digest[-4:], "big") % 100
    return (
        Buyer.OnboardingVariant.PAYWALL_FIRST
        if bucket < percent
        else Buyer.OnboardingVariant.TRIAL_FIRST
    )


def calculate_initial_expiry(variant: str) -> datetime:
    now = timezone.now()
    if variant == Buyer.OnboardingVariant.PAYWALL_FIRST:
        return now
    trial_days: Any = getattr(settings, "ONBOARDING_TRIAL_DAYS", DEFAULT_TRIAL_DAYS)
    if not isinstance(trial_days, int) or trial_days <= 0:
        trial_days = DEFAULT_TRIAL_DAYS
    return now + timedelta(days=trial_days)

