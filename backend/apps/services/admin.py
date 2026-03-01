from django.contrib import admin

from .models import Service, Staff, WorkingHours


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'tenant', 'name', 'duration_minutes', 'price', 'is_active')
    list_filter = ('tenant', 'is_active')
    search_fields = ('name',)


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ('id', 'tenant', 'name', 'phone', 'is_active')
    list_filter = ('tenant', 'is_active')
    search_fields = ('name', 'phone')


@admin.register(WorkingHours)
class WorkingHoursAdmin(admin.ModelAdmin):
    list_display = ('id', 'tenant', 'weekday', 'start_time', 'end_time', 'is_working_day')
    list_filter = ('tenant', 'weekday', 'is_working_day')
