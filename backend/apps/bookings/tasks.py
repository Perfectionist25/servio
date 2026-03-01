from datetime import timedelta

from aiogram import Bot
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import Booking


@shared_task
def send_booking_reminders():
    if not settings.TELEGRAM_BOT_TOKEN:
        return 'missing-bot-token'

    now = timezone.now()
    window_start = now + timedelta(hours=2)
    window_end = window_start + timedelta(minutes=1)

    bookings = Booking.objects.filter(
        status=Booking.STATUS_CONFIRMED,
        start_datetime__gte=window_start,
        start_datetime__lt=window_end,
        customer__telegram_id__isnull=False,
    ).select_related('customer', 'service', 'tenant')

    if not bookings.exists():
        return 'no-bookings'

    async def _send_all():
        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        for booking in bookings:
            text = (
                f'Напоминание о записи\n'
                f'Бизнес: {booking.tenant.name}\n'
                f'Услуга: {booking.service.name}\n'
                f'Время: {booking.start_datetime.astimezone().strftime("%Y-%m-%d %H:%M")}'
            )
            await bot.send_message(chat_id=booking.customer.telegram_id, text=text)
        await bot.session.close()

    import asyncio

    asyncio.run(_send_all())
    return f'sent-{bookings.count()}'
