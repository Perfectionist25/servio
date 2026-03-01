from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers

from apps.accounts.models import Customer
from apps.services.models import Service
from .models import Booking


class BookingCreateSerializer(serializers.ModelSerializer):
    customer_telegram_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Booking
        fields = (
            'id',
            'tenant',
            'customer_telegram_id',
            'service',
            'staff',
            'start_datetime',
            'end_datetime',
            'status',
            'comment',
        )
        read_only_fields = ('end_datetime',)

    def validate(self, attrs):
        service: Service = attrs['service']
        tenant_id = attrs['tenant'].id
        if service.tenant_id != tenant_id:
            raise serializers.ValidationError('Service does not belong to tenant.')

        staff = attrs.get('staff')
        if staff and staff.tenant_id != tenant_id:
            raise serializers.ValidationError('Staff does not belong to tenant.')

        start_dt = attrs['start_datetime']
        if timezone.is_naive(start_dt):
            raise serializers.ValidationError('start_datetime must be timezone-aware.')
        if start_dt <= timezone.now():
            raise serializers.ValidationError('start_datetime must be in the future.')

        attrs['end_datetime'] = start_dt + timedelta(minutes=service.duration_minutes)
        return attrs

    def create(self, validated_data):
        telegram_id = validated_data.pop('customer_telegram_id')
        customer, _ = Customer.objects.get_or_create(
            telegram_id=telegram_id,
            defaults={'full_name': f'TG {telegram_id}'}
        )

        start_dt = validated_data['start_datetime']
        end_dt = validated_data['end_datetime']
        tenant = validated_data['tenant']
        staff = validated_data.get('staff')

        conflict_filter = Q(tenant=tenant, start_datetime__lt=end_dt, end_datetime__gt=start_dt)
        if staff:
            conflict_filter &= Q(staff=staff)

        conflict_exists = Booking.objects.filter(conflict_filter).exclude(
            status=Booking.STATUS_CANCELLED
        ).exists()
        if conflict_exists:
            raise serializers.ValidationError('Selected time slot is not available.')

        validated_data['customer'] = customer
        return super().create(validated_data)


class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = (
            'id',
            'tenant',
            'customer',
            'service',
            'staff',
            'start_datetime',
            'end_datetime',
            'status',
            'created_at',
            'comment',
        )
