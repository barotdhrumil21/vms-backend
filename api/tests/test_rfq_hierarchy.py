from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from api.models import (
    Buyer,
    RequestForQuotation,
    RequestForQuotationItems,
    RequestForQuotationItemResponse,
    RFQItemAttachment,
)


class RFQHierarchyTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("buyer@example.com", password="strongpassword123")
        self.buyer = Buyer.objects.create(
            user=self.user,
            subscription_expiry_date=timezone.now() + timezone.timedelta(days=30),
            company_name="Test Buyer",
        )
        self.client.force_authenticate(user=self.user)

        self.rfq = RequestForQuotation.objects.create(buyer=self.buyer, title="Electronics Batch")
        self.item = RequestForQuotationItems.objects.create(
            request_for_quotation=self.rfq,
            product_name="Resistor",
            quantity=1000,
            uom="pcs",
            specifications="1k Ohm",
        )
        RequestForQuotationItemResponse.objects.create(
            request_for_quotation_item=self.item,
            quantity=1000,
            price=0.05,
        )
        RFQItemAttachment.objects.create(
            rfq_item=self.item,
            file="rfq-attachments/example.pdf",
            original_filename="spec.pdf",
            file_size=512,
            file_type="application/pdf",
            uploaded_by=self.user,
        )

    def test_create_rfq_requires_title(self):
        response = self.client.post(
            reverse("create-rfq"),
            {"items": [{"product_name": "Test", "quantity": 1, "uom": "pcs"}]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("title", response.json()["error"].lower())

    def test_get_rfq_list_returns_summary(self):
        response = self.client.get(reverse("get-rfq-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertEqual(len(payload["data"]), 1)
        summary = payload["meta"]["summary"]
        self.assertEqual(summary["total_rfqs"], 1)
        self.assertEqual(summary["total_items"], 1)
        self.assertEqual(summary["open_items"], 1)

    def test_get_rfq_list_filters_by_status(self):
        self.item.status = RequestForQuotationItems.CLOSE
        self.item.save()
        response = self.client.get(reverse("get-rfq-list"), {"status": "open"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["data"]), 0)

    def test_get_rfq_items_returns_attachments(self):
        response = self.client.get(reverse("get-rfq-items", args=[self.rfq.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertEqual(len(payload["items"]), 1)
        attachments = payload["items"][0]["attachments"]
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments[0]["filename"], "spec.pdf")

    def test_get_rfq_items_supports_search(self):
        RequestForQuotationItems.objects.create(
            request_for_quotation=self.rfq,
            product_name="Capacitor",
            quantity=200,
            uom="pcs",
        )
        response = self.client.get(reverse("get-rfq-items", args=[self.rfq.id]), {"q": "cap"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        self.assertEqual(len(payload["items"]), 1)
        self.assertEqual(payload["items"][0]["product_name"], "Capacitor")

