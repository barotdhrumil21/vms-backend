import shutil
import tempfile

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from api.models import AuditLog, Buyer, RequestForQuotation, RequestForQuotationItems, RFQItemAttachment


class RFQAttachmentAPITests(APITestCase):
    def setUp(self):
        self.temp_media = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.temp_media)
        self.override.enable()
        self.addCleanup(lambda: shutil.rmtree(self.temp_media, ignore_errors=True))
        self.addCleanup(self.override.disable)

        self.user = User.objects.create_user("user@example.com", password="strongpassword123")
        self.buyer = Buyer.objects.create(
            user=self.user,
            subscription_expiry_date=timezone.now() + timezone.timedelta(days=30),
            company_name="Test Co",
        )
        self.client.force_authenticate(user=self.user)

        self.rfq = RequestForQuotation.objects.create(buyer=self.buyer)
        self.rfq_item = RequestForQuotationItems.objects.create(
            request_for_quotation=self.rfq,
            product_name="Test Product",
            quantity=10,
            uom="pcs",
        )

    def _upload(self, name="test.pdf", content=b"%PDF-1.4 example", content_type="application/pdf", item=None):
        item = item or self.rfq_item
        upload_url = reverse("upload-rfq-item-attachment", args=[item.id])
        file_obj = SimpleUploadedFile(name, content, content_type=content_type)
        return self.client.post(upload_url, data={"file": file_obj}, format="multipart")

    def _json(self, response):
        try:
            return response.json()
        except AttributeError:
            import json
            return json.loads(response.content.decode())

    def test_upload_valid_attachment_returns_metadata(self):
        response = self._upload()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = self._json(response)
        self.assertTrue(payload["success"])
        attachment = payload["attachment"]
        self.assertEqual(attachment["filename"], "test.pdf")
        self.assertEqual(RFQItemAttachment.objects.count(), 1)
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.Actions.FILE_UPLOAD, resource_id=str(attachment["id"])
            ).exists()
        )

    def test_upload_rejects_large_file(self):
        with override_settings(RFQ_ATTACHMENT_MAX_SIZE_MB=1):
            big_content = b"x" * (2 * 1024 * 1024)
            response = self._upload(name="big.pdf", content=big_content)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file", self._json(response)["error"].lower())

    def test_upload_rejects_invalid_extension(self):
        response = self._upload(name="script.exe", content=b"MZ", content_type="application/octet-stream")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("unsupported", self._json(response)["error"].lower())

    def test_upload_enforces_storage_quota(self):
        with override_settings(RFQ_ATTACHMENT_STORAGE_QUOTA_MB=0):
            response = self._upload()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("quota", self._json(response)["error"].lower())

    def test_list_attachments_returns_entries(self):
        self._upload()
        list_url = reverse("list-rfq-item-attachments", args=[self.rfq_item.id])
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = self._json(response)
        self.assertTrue(payload["success"])
        self.assertEqual(len(payload["attachments"]), 1)
        self.assertEqual(payload["attachments"][0]["filename"], "test.pdf")

    def test_delete_attachment_removes_record_and_logs(self):
        upload_response = self._upload()
        attachment_id = self._json(upload_response)["attachment"]["id"]
        delete_url = reverse("delete-rfq-item-attachment", args=[attachment_id])
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(RFQItemAttachment.objects.filter(id=attachment_id).exists())
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.Actions.FILE_DELETE, resource_id=str(attachment_id)
            ).exists()
        )

    def test_download_attachment_streams_file(self):
        upload_response = self._upload()
        attachment_id = self._json(upload_response)["attachment"]["id"]
        download_url = reverse("download-rfq-item-attachment", args=[attachment_id])
        response = self.client.get(download_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.streaming)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_cannot_access_foreign_items(self):
        other_user = User.objects.create_user("other@example.com", password="pass12345")
        other_buyer = Buyer.objects.create(
            user=other_user,
            subscription_expiry_date=timezone.now() + timezone.timedelta(days=30)
        )
        other_rfq = RequestForQuotation.objects.create(buyer=other_buyer)
        other_item = RequestForQuotationItems.objects.create(
            request_for_quotation=other_rfq,
            product_name="Other",
            quantity=1,
            uom="pcs",
        )
        response = self._upload(item=other_item)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("rfq item not found", self._json(response)["error"].lower())
