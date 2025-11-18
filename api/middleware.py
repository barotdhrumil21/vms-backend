from datetime import timedelta

from django.http import JsonResponse
from django.utils import timezone
from django.conf import settings


class SubscriptionMiddleware:
    """Enforce subscription requirements for authenticated users."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.public_paths = (
            "/authentication/login/",
            "/authentication/signup/",
            "/auth/login/",
            "/auth/signup/",
            "/api/create-user/",
            "/rfq-response/",
        )
        self.subscription_exempt_paths = (
            "/authentication/user-details/",
            "/api/subscription-status/",
            "/membership/",
            "/static/",
            "/media/",
            "/admin/",
        )
        self.grace_period = timedelta(
            days=getattr(settings, "SUBSCRIPTION_GRACE_PERIOD_DAYS", 3)
        )

    def __call__(self, request):
        path = request.path

        if any(path.startswith(p) for p in self.public_paths):
            return self.get_response(request)

        user = getattr(request, "user", None)
        if not getattr(user, "is_authenticated", False):
            forced_user = getattr(request, "_force_auth_user", None)
            if forced_user is not None:
                user = forced_user
            else:
                return self.get_response(request)

        if user is None or getattr(user, "is_staff", False):
            return self.get_response(request)

        if any(path.startswith(p) for p in self.subscription_exempt_paths):
            return self.get_response(request)

        request.META["SUBSCRIPTION_CHECKED"] = True

        buyer = getattr(user, "buyer", None)
        if buyer is None or not buyer.subscription_expiry_date:
            return self._expired_response()

        now = timezone.now()
        expiry = buyer.subscription_expiry_date

        if now <= expiry:
            return self.get_response(request)

        if now <= expiry + self.grace_period:
            response = self.get_response(request)
            response["X-Subscription-Warning"] = "Subscription expired. Grace period active."
            return response

        return self._expired_response()

    @staticmethod
    def _expired_response():
        payload = {
            "success": False,
            "subscription_expired": True,
            "redirect_to": "/membership",
        }
        response = JsonResponse(payload, status=403)
        response.data = payload
        return response
