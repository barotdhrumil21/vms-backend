from api import views
from django.urls import path

urlpatterns = [
    path('create-supplier/', views.CreateSupplier.as_view(),name="create-supplier"),
]
