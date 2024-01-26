from django.db import models
from django.contrib.auth.models import User
import uuid

# Create your models here.

class Buyer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='buyer')
    phone_no = models.CharField(max_length = 12, null = True, blank=True)
    company_name = models.CharField(max_length = 255, null = True, blank=True)
    gst_no = models.CharField(max_length = 50, null = True, blank=True)
    Address = models.CharField(max_length = 255, null = True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now = True)


class Supplier(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    buyer = models.ForeignKey("api.Buyer",null=True,on_delete=models.SET_NULL,related_name="suppliers")
    company_name = models.TextField(max_length=255)
    person_of_contact = models.CharField(max_length=255)
    phone_no = models.CharField(max_length=12,null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    remark = models.TextField(null=True, blank=True)
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
    OPEN = 1
    CLOSE = 2
    STATUS_CHOICE = (
        (OPEN, "Open"),
        (CLOSE, "Close")
    )
    buyer = models.ForeignKey("api.Buyer",null=True,on_delete=models.SET_NULL,related_name="request_for_quotations")
    status = models.SmallIntegerField(choices = STATUS_CHOICE, default=OPEN)
    suppliers = models.ManyToManyField(Supplier,related_name="request_for_quotations")
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now = True)

class RequestForQuotationMetaData(models.Model):
    terms_conditions = models.TextField(null=True, blank=True)
    payment_terms = models.TextField(null=True, blank=True)
    shipping_terms = models.TextField(null=True, blank=True)
    request_for_quotation = models.ForeignKey("api.RequestForQuotation",null=True,on_delete=models.SET_NULL,related_name="request_for_quotation_meta_data")
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now = True)
    
class RequestForQuotationItems(models.Model):
    request_for_quotation = models.ForeignKey("api.RequestForQuotation",null=True,on_delete=models.SET_NULL,related_name="request_for_quotation_items")
    product_name = models.TextField()
    quantity = models.FloatField()
    uom = models.CharField(max_length=50,null=True, blank=True)
    specifications = models.TextField(null=True, blank=True)
    expected_delivery_date = models.DateField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now = True)
    
    
    
    
    
    
    
    