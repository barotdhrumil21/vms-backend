from django.conf import settings
from django.contrib.auth.models import User
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from api.ab_testing import pick_subscription_variant, calculate_initial_expiry
from api.models import Buyer, RequestForQuotation


class SubscriptionTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("sub@example.com", password="strongpassword123")
        self.buyer = Buyer.objects.create(
            user=self.user,
            subscription_expiry_date=timezone.now() + timezone.timedelta(days=5),
            onboarding_variant=Buyer.OnboardingVariant.TRIAL_FIRST,
        )
        self.client.force_authenticate(user=self.user)

    def test_subscription_status_endpoint_returns_flags(self):
        RequestForQuotation.objects.create(buyer=self.buyer, title="Test RFQ")
        url = reverse("subscription-status")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertTrue(data["is_active"])
        self.assertFalse(data["subscription_expired"])
        self.assertEqual(data["variant"], Buyer.OnboardingVariant.TRIAL_FIRST)

    def test_subscription_middleware_blocks_expired_users(self):
        self.buyer.subscription_expiry_date = timezone.now() - timezone.timedelta(days=10)
        self.buyer.save(update_fields=["subscription_expiry_date"])
        url = reverse("get-rfq-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(response.data["success"])
        self.assertTrue(response.data["subscription_expired"])

    def test_subscription_middleware_allows_grace_period(self):
        with override_settings(SUBSCRIPTION_GRACE_PERIOD_DAYS=5):
            self.buyer.subscription_expiry_date = timezone.now() - timezone.timedelta(days=2)
            self.buyer.save(update_fields=["subscription_expiry_date"])
            RequestForQuotation.objects.create(buyer=self.buyer, title="Grace RFQ")
            url = reverse("get-rfq-list")
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn("X-Subscription-Warning", response)

    def test_ab_testing_helpers_are_deterministic(self):
        identifier = "test@example.com"
        variant_first = pick_subscription_variant(identifier)
        variant_second = pick_subscription_variant(identifier)
        self.assertEqual(variant_first, variant_second)

        paywall_expiry = calculate_initial_expiry(Buyer.OnboardingVariant.PAYWALL_FIRST)
        self.assertLess((paywall_expiry - timezone.now()).total_seconds(), 5)

        trial_expiry = calculate_initial_expiry(Buyer.OnboardingVariant.TRIAL_FIRST)
        expected_days = getattr(settings, "ONBOARDING_TRIAL_DAYS", 45)
        delta_days = (trial_expiry.date() - timezone.now().date()).days
        self.assertAlmostEqual(delta_days, expected_days, delta=1)
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from api.ab_testing import calculate_initial_expiry, pick_subscription_variant
from api.models import Buyer


class ABTestingHelperTests(TestCase):
    def test_variant_is_deterministic(self):
        first = pick_subscription_variant("member@example.com")
        second = pick_subscription_variant("member@example.com")
        self.assertEqual(first, second)

    @override_settings(SUBSCRIPTION_PAYWALL_PERCENT=0)
    def test_zero_percent_enforces_trial(self):
        variant = pick_subscription_variant("trial@example.com")
        self.assertEqual(variant, Buyer.OnboardingVariant.TRIAL_FIRST)

    @override_settings(SUBSCRIPTION_PAYWALL_PERCENT=100)
    def test_full_percent_enforces_paywall(self):
        variant = pick_subscription_variant("paywall@example.com")
        self.assertEqual(variant, Buyer.OnboardingVariant.PAYWALL_FIRST)

    def test_calculate_initial_expiry_for_paywall_is_now(self):
        expiry = calculate_initial_expiry(Buyer.OnboardingVariant.PAYWALL_FIRST)
        delta = abs((expiry - timezone.now()).total_seconds())
        self.assertLess(delta, 2)

    def test_calculate_initial_expiry_for_trial_in_future(self):
        expiry = calculate_initial_expiry(Buyer.OnboardingVariant.TRIAL_FIRST)
        self.assertGreater(expiry, timezone.now())


@override_settings(SUBSCRIPTION_GRACE_PERIOD_DAYS=3)
class SubscriptionMiddlewareTests(APITestCase):
    def setUp(self):
        self.client: APIClient = APIClient()
        self.user = User.objects.create_user("member@example.com", password="password123")
        self.buyer = Buyer.objects.create(
            user=self.user,
            subscription_expiry_date=timezone.now() + timedelta(days=5),
            company_name="Test Buyer",
        )
        self.client.login(username="member@example.com", password="password123")

    def test_active_subscription_allows_access(self):
        response = self.client.get("/api/get-rfq-list/")
        self.assertTrue(response.wsgi_request.META.get("SUBSCRIPTION_CHECKED"))
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_grace_period_allows_access_with_warning_header(self):
        self.buyer.subscription_expiry_date = timezone.now() - timedelta(days=1)
        self.buyer.save(update_fields=["subscription_expiry_date"])
        self.buyer.refresh_from_db()
        response = self.client.get("/api/get-rfq-list/")
        self.assertTrue(response.wsgi_request.META.get("SUBSCRIPTION_CHECKED"))
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIsNotNone(response.headers.get("X-Subscription-Warning"))

    def test_expired_subscription_blocked(self):
        self.buyer.subscription_expiry_date = timezone.now() - timedelta(days=10)
        self.buyer.save(update_fields=["subscription_expiry_date"])
        self.buyer.refresh_from_db()
        response = self.client.get("/api/get-rfq-list/")
        self.assertTrue(response.wsgi_request.META.get("SUBSCRIPTION_CHECKED"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(response.json().get("subscription_expired"))

    def test_subscription_status_endpoint(self):
        response = self.client.get("/api/subscription-status/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertTrue(payload["data"]["is_active"])
