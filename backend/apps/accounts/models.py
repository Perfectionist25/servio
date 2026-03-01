from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import UserManager


class User(AbstractUser):
    ROLE_SUPERADMIN = 'superadmin'
    ROLE_OWNER = 'owner'
    ROLE_STAFF = 'staff'

    ROLE_CHOICES = [
        (ROLE_SUPERADMIN, 'SuperAdmin'),
        (ROLE_OWNER, 'Owner'),
        (ROLE_STAFF, 'Staff'),
    ]

    telegram_id = models.BigIntegerField(null=True, blank=True, unique=True)
    tenant = models.ForeignKey('tenants.Tenant', null=True, blank=True, on_delete=models.SET_NULL, related_name='users')
    role = models.CharField(max_length=16, choices=ROLE_CHOICES, default=ROLE_STAFF)
    phone = models.CharField(max_length=32, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    class Meta:
        indexes = [
            models.Index(fields=['tenant', 'role']),
        ]

    def __str__(self) -> str:
        return f'{self.username} ({self.role})'


class Customer(models.Model):
    telegram_id = models.BigIntegerField(unique=True)
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=32, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.full_name} ({self.telegram_id})'
