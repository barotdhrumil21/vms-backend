from api import views
from django.urls import path

urlpatterns = [
    path('create-supplier/', views.CreateSupplier.as_view(),name="create-supplier"),
    path('get-suppliers/', views.GetSuppliers.as_view(),name="create-supplier"),
    path('create-rfq/', views.CreateRFQ.as_view(),name="create-rfq"),
    path('get-rfq-metadata/', views.GetMetaData.as_view(),name="get-rfq-metadata"),
    path('get-supplier-categories/', views.GetSupplierCategories.as_view(),name="get-supplier-categories"),
    
    
    
]
