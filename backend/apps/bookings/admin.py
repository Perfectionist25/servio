from django.contrib import admin

from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'tenant', 'customer', 'service', 'staff', 'start_datetime', 'status', 'created_at')
    list_filter = ('tenant', 'status', 'start_datetime', 'created_at')
    search_fields = ('customer__full_name', 'customer__phone', 'tenant__name', 'service__name')
    date_hierarchy = 'start_datetime'
