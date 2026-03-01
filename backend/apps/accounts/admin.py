from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Customer, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        (
            'Servio',
            {
                'fields': ('telegram_id', 'tenant', 'role', 'phone', 'created_at'),
            },
        ),
    )
    readonly_fields = ('created_at',)
    list_display = ('id', 'username', 'role', 'tenant', 'is_active', 'is_staff', 'created_at')
    list_filter = ('role', 'tenant', 'is_active', 'is_staff')
    search_fields = ('username', 'phone', 'telegram_id')


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'phone', 'telegram_id', 'created_at')
    search_fields = ('full_name', 'phone', 'telegram_id')
    readonly_fields = ('created_at',)
