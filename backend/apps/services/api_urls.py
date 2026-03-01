from django.urls import path

from .views import ServiceListAPIView

urlpatterns = [
    path('tenants/<int:tenant_id>/services/', ServiceListAPIView.as_view(), name='service-list'),
]
