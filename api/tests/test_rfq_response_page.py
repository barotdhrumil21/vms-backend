from datetime import timedelta

from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from api.models import (
    Buyer,
    RequestForQuotation,
    RequestForQuotationItems,
    RequestForQuotationItemResponse,
    RequestForQuotationMetaData,
    Supplier,
)


class RFQResponsePageDataTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("buyer@example.com", password="strong-password-123")
        self.buyer = Buyer.objects.create(
            user=self.user,
            subscription_expiry_date=timezone.now() + timedelta(days=30),
            company_name="Acme Corp",
        )
        self.rfq = RequestForQuotation.objects.create(buyer=self.buyer, title="Test RFQ")
        self.supplier = Supplier.objects.create(
            buyer=self.buyer,
            company_name="Widget Supplies",
            person_of_contact="Jane Vendor",
            phone_no="+1-555-0100",
            email="jane@example.com",
        )
        self.rfq.suppliers.add(self.supplier)
        self.rfq_item = RequestForQuotationItems.objects.create(
            request_for_quotation=self.rfq,
            product_name="Widget",
            quantity=5,
            uom="pcs",
        )

    def test_returns_defaults_when_metadata_missing(self):
        url = reverse("get-rfq-response", args=[self.rfq.id, str(self.supplier.id)])
        response = self.client.get(url)
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["data"]["terms_conditions"], "No terms")
        self.assertEqual(payload["data"]["payment_terms"], "No terms")
        self.assertEqual(payload["data"]["shipping_terms"], "No terms")
        self.assertEqual(len(payload["data"]["items"]), 1)

    def test_includes_existing_supplier_response_details(self):
        RequestForQuotationMetaData.objects.create(
            request_for_quotation=self.rfq,
            terms_conditions="Sample terms",
            payment_terms="Net 30",
            shipping_terms="FOB",
        )
        RequestForQuotationItemResponse.objects.create(
            request_for_quotation_item=self.rfq_item,
            supplier=self.supplier,
            quantity=7,
            price=15.5,
            lead_time=4,
            remarks="Fast delivery",
        )

        url = reverse("get-rfq-response", args=[self.rfq.id, str(self.supplier.id)])
        response = self.client.get(url)
        payload = response.json()
        item = payload["data"]["items"][0]

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["success"])
        self.assertTrue(item["responded"])
        self.assertEqual(item["supplier_price"], 15.5)
        self.assertEqual(item["supplier_quantity"], 7)
        self.assertEqual(item["supplier_lead_time"], 4)
        self.assertEqual(item["supplier_remarks"], "Fast delivery")



