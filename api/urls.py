from api import views
from django.urls import path

urlpatterns = [
    path('create-supplier/', views.CreateSupplier.as_view(),name="create-supplier"),
    path('create-user/', views.CreateUser.as_view(),name="create-user"),
    path('framer-create-user/', views.FramerCreateUser.as_view(),name="framer-create-user"),
    path('get-suppliers/', views.GetSuppliers.as_view(),name="get-suppliers"),
    path('create-rfq/', views.CreateRFQ.as_view(),name="create-rfq"),
    path('get-rfq/', views.GetRFQ.as_view(),name="get-rfq"),
    path('get-rfq-metadata/', views.GetMetaData.as_view(),name="get-rfq-metadata"),
    path('get-supplier-categories/', views.GetSupplierCategories.as_view(),name="get-supplier-categories"),
    path('get-item-uom/', views.GetRfqUom.as_view(),name="get-item-uom"),
    path('get-item-product/', views.GetRfqProduct.as_view(),name="get-item-product"),
    path('get-rfq-response/<int:rfq_id>/<str:supplier_id>/', views.GetRFQResponsePageData.as_view(),name="get-supplier-categories"),
    path('create-rfq-response/', views.CreateRFQResponse.as_view(),name="create-rfq-response"),
    path('rfq-item-data/<int:rfq_item_id>', views.RFQItemData.as_view(),name="rfq-item-data"),
    path('send-rfq-data-file/', views.GetAllRFQDataEmail.as_view(),name="send-rfq-data-file"),
    path('get-supplier-stats-data/', views.GetSuppliersStatsData.as_view(),name="get-supplier-stats-data"),
    path('import-suppliers/', views.BulkImportSuppliers.as_view(),name="bulk-import-suppliers"),
    path('send-reminders/', views.SendRFQReminder.as_view(),name="send-rfq-reminders-to-suppliers"),
]
