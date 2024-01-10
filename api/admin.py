from django.contrib import admin
from api import models
# Register your models here.
admin.site.register(models.Buyer)
admin.site.register(models.RequestQuotation)
admin.site.register(models.RequestForQuotationItems)
admin.site.register(models.RequestForQuotationMetaData)
admin.site.register(models.Supplier)




