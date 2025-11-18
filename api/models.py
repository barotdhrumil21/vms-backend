from django.db import models
from django.db.models import Sum
from django.contrib.auth.models import User
import uuid

# Create your models here.
class Buyer(models.Model):
    class OnboardingVariant(models.TextChoices):
        PAYWALL_FIRST = ("PAYWALL_FIRST", "Paywall First")
        TRIAL_FIRST = ("TRIAL_FIRST", "Trial First")

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='buyer')
    subscription_expiry_date = models.DateTimeField(auto_now_add=False)
    phone_no = models.CharField(max_length = 200, null = True, blank=True)
    company_name = models.CharField(max_length = 255, null = True, blank=True)
    gst_no = models.CharField(max_length = 50, null = True, blank=True)
    address = models.CharField(max_length = 255, null = True, blank=True)
    currency = models.CharField(max_length=50, null=True, blank=True)
    timezone = models.CharField(max_length=100, default="Asia/Kolkata", null=True, blank=True)
    test_user = models.BooleanField(default=False)
    onboarding_variant = models.CharField(
        max_length=20,
        choices=OnboardingVariant.choices,
        default=OnboardingVariant.TRIAL_FIRST,
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now = True)

    def __str__(self):
        return self.company_name or self.user.username

    def get_used_storage_in_mb(self):
        total_bytes = (
            RFQItemAttachment.objects.filter(
                rfq_item__request_for_quotation__buyer=self
            ).aggregate(total_size=Sum("file_size")).get("total_size") or 0
        )
        return total_bytes / (1024 * 1024) if total_bytes else 0

class Supplier(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    buyer = models.ForeignKey("api.Buyer",null=True,on_delete=models.SET_NULL,related_name="suppliers")
    company_name = models.TextField(max_length=255)
    person_of_contact = models.CharField(max_length=255)
    phone_no = models.CharField(max_length=200,null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    remark = models.TextField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now = True)
    
class SupplierCategory(models.Model):
    buyer = models.ForeignKey("api.Buyer",null=True,on_delete=models.SET_NULL,related_name="supplier_categories")
    name = models.TextField()
    supplier = models.ForeignKey(Supplier,null=True, on_delete=models.SET_NULL,related_name="categories") 
    active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now = True)

class RequestForQuotation(models.Model):
    buyer = models.ForeignKey("api.Buyer",null=True,on_delete=models.SET_NULL,related_name="request_for_quotations")
    suppliers = models.ManyToManyField(Supplier,related_name="request_for_quotations")
    title = models.CharField(max_length=255, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now = True)

    def __str__(self):
        return self.get_display_title()

    def get_display_title(self):
        if self.title:
            return self.title
        return f"RFQ #{self.pk}"

class RequestForQuotationMetaData(models.Model):
    terms_conditions = models.TextField(null=True, blank=True)
    payment_terms = models.TextField(null=True, blank=True)
    shipping_terms = models.TextField(null=True, blank=True)
    request_for_quotation = models.ForeignKey("api.RequestForQuotation",null=True,on_delete=models.SET_NULL,related_name="request_for_quotation_meta_data")
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now = True)
    
class RequestForQuotationItems(models.Model):
    OPEN = 1
    CLOSE = 2
    STATUS_CHOICE = (
        (OPEN, "Open"),
        (CLOSE, "Close")
    )
    request_for_quotation = models.ForeignKey("api.RequestForQuotation",null=True,on_delete=models.SET_NULL,related_name="request_for_quotation_items")
    product_name = models.TextField()
    quantity = models.FloatField()
    uom = models.CharField(max_length=50,null=True, blank=True)
    status = models.SmallIntegerField(choices = STATUS_CHOICE, default=OPEN)
    specifications = models.TextField(null=True, blank=True)
    expected_delivery_date = models.DateField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now = True)

class RequestForQuotationItemResponse(models.Model):
    ORDER_PLACED = 1
    ORDER_PENDING = 2
    ORDER_STATUS = (
        (ORDER_PENDING,"Pending"),
        (ORDER_PLACED,"Placed")
    )
    
    request_for_quotation_item = models.ForeignKey("api.RequestForQuotationItems",null=True,on_delete=models.SET_NULL,related_name="request_for_quotation_item_response")
    quantity = models.FloatField() #moq field
    bought_price = models.FloatField(null=True, blank=True) #moq field
    bought_quantity = models.FloatField(null=True, blank=True)
    price = models.FloatField()
    supplier = models.ForeignKey(Supplier,null=True, on_delete=models.SET_NULL,related_name="request_for_quotation_responses") 
    order_status = models.SmallIntegerField(choices = ORDER_STATUS, default=ORDER_PENDING)
    delivery_date = models.DateField(null=True, blank=True)
    lead_time = models.IntegerField(null=True, blank=True)
    remarks = models.CharField(max_length=200,null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now = True)
    
    def save(self, *args, **kwargs):
        placed_response = self.request_for_quotation_item.request_for_quotation_item_response.filter(order_status=self.ORDER_PLACED)
        if placed_response.exists():
            raise Exception("Order already placed for this item")
        super(RequestForQuotationItemResponse,self).save(*args, **kwargs)
    
    
    
    
    
    
class RFQItemAttachment(models.Model):
    rfq_item = models.ForeignKey(
        "api.RequestForQuotationItems",
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    file = models.FileField(upload_to="rfq-attachments/%Y/%m/%d/")
    original_filename = models.CharField(max_length=255)
    file_size = models.BigIntegerField()
    file_type = models.CharField(max_length=100)
    uploaded_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="rfq_item_attachments",
    )
    checksum = models.CharField(max_length=128, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rfq_item_attachments"
        ordering = ["-created"]
        indexes = [
            models.Index(
                fields=["rfq_item", "-created"],
                name="rfq_attach_item_created_idx",
            )
        ]


class AuditLog(models.Model):
    class Actions(models.TextChoices):
        FILE_UPLOAD = ("file_upload", "File Upload")
        FILE_DELETE = ("file_delete", "File Delete")
        FILE_DOWNLOAD = ("file_download", "File Download")

    user = models.ForeignKey(
        User,
        null=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=50, choices=Actions.choices)
    resource_type = models.CharField(max_length=50)
    resource_id = models.CharField(max_length=100)
    details = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_logs"
        ordering = ["-created"]
        indexes = [
            models.Index(
                fields=["resource_type", "resource_id"],
                name="audit_resource_idx",
            ),
            models.Index(fields=["-created"], name="audit_created_idx"),
        ]
    
    