from django.urls import path

from .views import AvailableSlotsAPIView, BookingCreateAPIView, TenantBookingListAPIView

urlpatterns = [
    path('bookings/', BookingCreateAPIView.as_view(), name='booking-create'),
    path('tenants/<int:tenant_id>/bookings/', TenantBookingListAPIView.as_view(), name='tenant-bookings'),
    path('tenants/<int:tenant_id>/slots/', AvailableSlotsAPIView.as_view(), name='available-slots'),
]
