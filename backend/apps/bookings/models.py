from django.db import models


class Booking(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_COMPLETED = 'completed'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_COMPLETED, 'Completed'),
    ]

    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='bookings')
    customer = models.ForeignKey('accounts.Customer', on_delete=models.CASCADE, related_name='bookings')
    service = models.ForeignKey('services.Service', on_delete=models.PROTECT, related_name='bookings')
    staff = models.ForeignKey('services.Staff', null=True, blank=True, on_delete=models.SET_NULL, related_name='bookings')
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(blank=True)

    class Meta:
        ordering = ['start_datetime']
        indexes = [
            models.Index(fields=['tenant', 'start_datetime']),
            models.Index(fields=['status', 'start_datetime']),
        ]

    def __str__(self) -> str:
        return f'#{self.id} {self.tenant.slug} {self.start_datetime} ({self.status})'
