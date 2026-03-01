from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.db.models import Q
from django.utils import timezone

from apps.services.models import Service, WorkingHours
from .models import Booking


def get_available_slots(tenant, service: Service, target_date, slot_step_minutes: int = 30):
    tz = ZoneInfo(tenant.timezone)
    weekday = target_date.weekday()

    try:
        hours = WorkingHours.objects.get(tenant=tenant, weekday=weekday)
    except WorkingHours.DoesNotExist:
        return []

    if not hours.is_working_day:
        return []

    start_dt = datetime.combine(target_date, hours.start_time, tzinfo=tz)
    end_dt = datetime.combine(target_date, hours.end_time, tzinfo=tz)
    duration = timedelta(minutes=service.duration_minutes)
    step = timedelta(minutes=slot_step_minutes)

    day_bookings = Booking.objects.filter(
        tenant=tenant,
        start_datetime__lt=end_dt,
        end_datetime__gt=start_dt,
    ).exclude(status=Booking.STATUS_CANCELLED)

    slots = []
    current = start_dt
    while current + duration <= end_dt:
        candidate_end = current + duration
        busy = day_bookings.filter(
            Q(start_datetime__lt=candidate_end) & Q(end_datetime__gt=current)
        ).exists()
        if not busy and current > timezone.now():
            slots.append(current)
        current += step

    return slots
