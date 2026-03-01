from django.db import models


class Tenant(models.Model):
    PLAN_BASIC = 'basic'
    PLAN_PRO = 'pro'
    PLAN_ENTERPRISE = 'enterprise'

    PLAN_CHOICES = [
        (PLAN_BASIC, 'Basic'),
        (PLAN_PRO, 'Pro'),
        (PLAN_ENTERPRISE, 'Enterprise'),
    ]

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=64, unique=True)
    phone = models.CharField(max_length=32)
    address = models.CharField(max_length=512, blank=True)
    timezone = models.CharField(max_length=64, default='UTC')
    subscription_plan = models.CharField(max_length=32, choices=PLAN_CHOICES, default=PLAN_BASIC)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self) -> str:
        return f'{self.name} ({self.slug})'
