from django.contrib import admin

from .models import Tenant


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug', 'subscription_plan', 'is_active', 'created_at')
    list_filter = ('subscription_plan', 'is_active', 'created_at')
    search_fields = ('name', 'slug', 'phone')
    prepopulated_fields = {'slug': ('name',)}
