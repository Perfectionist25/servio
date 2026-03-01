from django.db import models


class Service(models.Model):
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='services')
    name = models.CharField(max_length=255)
    duration_minutes = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        indexes = [models.Index(fields=['tenant', 'is_active'])]

    def __str__(self) -> str:
        return f'{self.tenant.slug} - {self.name}'


class Staff(models.Model):
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='staff_members')
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=32, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        indexes = [models.Index(fields=['tenant', 'is_active'])]

    def __str__(self) -> str:
        return f'{self.name} ({self.tenant.slug})'


class WorkingHours(models.Model):
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='working_hours')
    weekday = models.PositiveSmallIntegerField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_working_day = models.BooleanField(default=True)

    class Meta:
        unique_together = ('tenant', 'weekday')
        ordering = ['tenant', 'weekday']

    def __str__(self) -> str:
        return f'{self.tenant.slug} day={self.weekday} {self.start_time}-{self.end_time}'
