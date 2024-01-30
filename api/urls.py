from api import views
from django.urls import path

urlpatterns = [
    path('create-supplier/', views.CreateSupplier.as_view(),name="create-supplier"),
    path('get-suppliers/', views.GetSuppliers.as_view(),name="get-suppliers"),
    path('create-rfq/', views.CreateRFQ.as_view(),name="create-rfq"),
    path('get-rfq/', views.GetRFQ.as_view(),name="get-rfq"),
    path('get-rfq-metadata/', views.GetMetaData.as_view(),name="get-rfq-metadata"),
    path('get-supplier-categories/', views.GetSupplierCategories.as_view(),name="get-supplier-categories"),
    path('get-rfq-response/<int:rfq_id>/<str:supplier_id>/', views.GetRFQResponsePageData.as_view(),name="get-supplier-categories"),
    path('create-rfq-response/', views.CreateRFQResponse.as_view(),name="create-rfq-response"),
    path('rfq-item-data/<int:rfq_item_id>', views.RFQItemData.as_view(),name="create-rfq-response"),
    

]
