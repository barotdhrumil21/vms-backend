from django.db import models
from django.contrib.auth.models import User
import uuid

# Create your models here.
class Buyer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='buyer')
    subscription_expiry_date = models.DateTimeField(auto_now_add=False)
    phone_no = models.CharField(max_length = 200, null = True, blank=True)
    company_name = models.CharField(max_length = 255, null = True, blank=True)
    gst_no = models.CharField(max_length = 50, null = True, blank=True)
    address = models.CharField(max_length = 255, null = True, blank=True)
    currency = models.CharField(max_length = 50, null = True, blank=True)
    test_user = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now = True)

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
    
    
    
    
    
    
    
    