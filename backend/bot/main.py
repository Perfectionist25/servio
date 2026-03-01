import asyncio
import os
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

import django
from asgiref.sync import sync_to_async
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from django.db.models import Count
from django.utils import timezone

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.accounts.models import Customer, User
from apps.bookings.models import Booking
from apps.bookings.services import get_available_slots
from apps.services.models import Service, Staff
from apps.tenants.models import Tenant


class BookingFlow(StatesGroup):
    choosing_tenant = State()
    choosing_service = State()
    choosing_date = State()
    choosing_slot = State()


def role_menu_keyboard(role: str):
    builder = InlineKeyboardBuilder()

    if role == User.ROLE_SUPERADMIN:
        builder.button(text='Бизнесы', callback_data='super:tenants')
        builder.button(text='Записи сегодня', callback_data='super:today')
        builder.button(text='Статистика', callback_data='super:stats')
        builder.adjust(1)
    elif role == User.ROLE_OWNER:
        builder.button(text='Мои услуги', callback_data='owner:services')
        builder.button(text='Мои сотрудники', callback_data='owner:staff')
        builder.button(text='Записи сегодня', callback_data='owner:today')
        builder.button(text='Ближайшие записи', callback_data='owner:upcoming')
        builder.adjust(1)
    elif role == User.ROLE_STAFF:
        builder.button(text='Записи сегодня', callback_data='staff:today')
        builder.button(text='Ближайшие записи', callback_data='staff:upcoming')
        builder.adjust(1)
    else:
        builder.button(text='Записаться', callback_data='customer:book')
        builder.button(text='Мои записи', callback_data='customer:bookings')
        builder.button(text='Отменить запись', callback_data='customer:cancel_menu')
        builder.adjust(1)

    return builder.as_markup()


def main_menu_keyboard(role: str):
    builder = InlineKeyboardBuilder()
    builder.button(text='Главное меню', callback_data=f'menu:{role}')
    builder.adjust(1)
    return builder.as_markup()


def date_keyboard():
    builder = InlineKeyboardBuilder()
    today = timezone.localdate()
    for i in range(7):
        d = today + timedelta(days=i)
        builder.button(text=d.strftime('%d.%m (%a)'), callback_data=f'date:{d.isoformat()}')
    builder.adjust(2)
    return builder.as_markup()


async def tenant_keyboard(tenants_data):
    builder = InlineKeyboardBuilder()
    for tenant_id, tenant_name in tenants_data:
        builder.button(text=tenant_name, callback_data=f'tenant:{tenant_id}')
    builder.adjust(1)
    return builder.as_markup()


async def service_keyboard(services_data):
    builder = InlineKeyboardBuilder()
    for service_id, service_name, duration_minutes in services_data:
        builder.button(text=f'{service_name} ({duration_minutes} мин)', callback_data=f'service:{service_id}')
    builder.adjust(1)
    return builder.as_markup()


def slot_keyboard(slots):
    builder = InlineKeyboardBuilder()
    for slot in slots[:24]:
        builder.button(text=slot.strftime('%H:%M'), callback_data=f'slot:{slot.isoformat()}')
    builder.adjust(4)
    return builder.as_markup()


def cancel_booking_keyboard(items):
    builder = InlineKeyboardBuilder()
    for booking_id, tenant_name, service_name, start_dt in items:
        text = f'#{booking_id} {tenant_name} | {service_name} | {start_dt.strftime("%d.%m %H:%M")}'
        builder.button(text=text, callback_data=f'cancel:{booking_id}')
    builder.adjust(1)
    return builder.as_markup()


def _resolve_role_and_user(telegram_id: int):
    user = User.objects.filter(telegram_id=telegram_id, is_active=True).select_related('tenant').first()
    if user and user.role in {User.ROLE_SUPERADMIN, User.ROLE_OWNER, User.ROLE_STAFF}:
        return user.role, user
    return 'customer', None


def _ensure_customer(telegram_id: int, full_name: str):
    return Customer.objects.update_or_create(
        telegram_id=telegram_id,
        defaults={'full_name': full_name or f'user_{telegram_id}'},
    )


def _get_active_tenants_for_role(role: str, user: User | None):
    if role in {User.ROLE_OWNER, User.ROLE_STAFF} and user and user.tenant_id:
        return list(
            Tenant.objects.filter(id=user.tenant_id, is_active=True)
            .order_by('name')
            .values_list('id', 'name')
        )
    return list(Tenant.objects.filter(is_active=True).order_by('name').values_list('id', 'name'))


def _get_active_services(tenant_id: int):
    return list(
        Service.objects.filter(tenant_id=tenant_id, is_active=True)
        .order_by('name')
        .values_list('id', 'name', 'duration_minutes')
    )


def _get_customer_bookings(telegram_id: int):
    now = timezone.now()
    return list(
        Booking.objects.filter(customer__telegram_id=telegram_id, start_datetime__gte=now)
        .exclude(status=Booking.STATUS_CANCELLED)
        .select_related('tenant', 'service')
        .order_by('start_datetime')[:10]
        .values_list('id', 'tenant__name', 'service__name', 'start_datetime', 'status')
    )


def _get_customer_cancellable_bookings(telegram_id: int):
    now = timezone.now()
    return list(
        Booking.objects.filter(
            customer__telegram_id=telegram_id,
            start_datetime__gte=now,
            status__in=[Booking.STATUS_PENDING, Booking.STATUS_CONFIRMED],
        )
        .select_related('tenant', 'service')
        .order_by('start_datetime')[:10]
        .values_list('id', 'tenant__name', 'service__name', 'start_datetime')
    )


def _cancel_customer_booking(telegram_id: int, booking_id: int):
    updated = Booking.objects.filter(
        id=booking_id,
        customer__telegram_id=telegram_id,
        status__in=[Booking.STATUS_PENDING, Booking.STATUS_CONFIRMED],
    ).update(status=Booking.STATUS_CANCELLED)
    return updated > 0


def _format_booking_rows(rows):
    if not rows:
        return 'Записей нет.'
    lines = []
    for item in rows:
        booking_id, tenant_name, service_name, start_dt, status = item
        lines.append(
            f'#{booking_id} | {tenant_name} | {service_name} | '
            f'{start_dt.astimezone().strftime("%Y-%m-%d %H:%M")} | {status}'
        )
    return '\n'.join(lines)


def _owner_or_staff_bookings(tenant_id: int, days: int):
    now = timezone.now()
    end = now + timedelta(days=days)
    return list(
        Booking.objects.filter(tenant_id=tenant_id, start_datetime__gte=now, start_datetime__lt=end)
        .exclude(status=Booking.STATUS_CANCELLED)
        .select_related('customer', 'service')
        .order_by('start_datetime')[:20]
        .values_list('id', 'customer__full_name', 'service__name', 'start_datetime', 'status')
    )


def _superadmin_today_bookings():
    now = timezone.now()
    start = datetime.combine(now.date(), time.min, tzinfo=now.tzinfo)
    end = datetime.combine(now.date(), time.max, tzinfo=now.tzinfo)
    return list(
        Booking.objects.filter(start_datetime__gte=start, start_datetime__lte=end)
        .exclude(status=Booking.STATUS_CANCELLED)
        .select_related('tenant', 'service', 'customer')
        .order_by('start_datetime')[:40]
        .values_list('id', 'tenant__name', 'customer__full_name', 'service__name', 'start_datetime', 'status')
    )


def _superadmin_stats():
    now = timezone.now()
    tenants_total = Tenant.objects.count()
    tenants_active = Tenant.objects.filter(is_active=True).count()
    bookings_today = Booking.objects.filter(start_datetime__date=now.date()).count()
    bookings_future = Booking.objects.filter(start_datetime__gte=now).exclude(status=Booking.STATUS_CANCELLED).count()
    customers = Customer.objects.count()
    return {
        'tenants_total': tenants_total,
        'tenants_active': tenants_active,
        'bookings_today': bookings_today,
        'bookings_future': bookings_future,
        'customers': customers,
    }


def _superadmin_tenants():
    return list(
        Tenant.objects.annotate(bookings_count=Count('bookings'))
        .order_by('name')
        .values_list('name', 'is_active', 'subscription_plan', 'bookings_count')
    )


def _owner_services(tenant_id: int):
    return list(
        Service.objects.filter(tenant_id=tenant_id, is_active=True)
        .order_by('name')
        .values_list('name', 'duration_minutes', 'price')
    )


def _owner_staff(tenant_id: int):
    return list(
        Staff.objects.filter(tenant_id=tenant_id, is_active=True)
        .order_by('name')
        .values_list('name', 'phone')
    )


def _create_booking(tenant, customer, service, slot_dt):
    return Booking.objects.create(
        tenant=tenant,
        customer=customer,
        service=service,
        start_datetime=slot_dt,
        end_datetime=slot_dt + timedelta(minutes=service.duration_minutes),
        status=Booking.STATUS_CONFIRMED,
    )


async def show_main_menu(message: Message, telegram_id: int, full_name: str):
    role, user = await sync_to_async(_resolve_role_and_user, thread_sensitive=True)(telegram_id)
    if role == 'customer':
        await sync_to_async(_ensure_customer, thread_sensitive=True)(telegram_id, full_name)
        await message.answer('Меню клиента:', reply_markup=role_menu_keyboard(role))
        return

    await message.answer(f'Меню роли: {role}', reply_markup=role_menu_keyboard(role))


async def start_handler(message: Message, state: FSMContext):
    await state.clear()
    tg_user = message.from_user
    await show_main_menu(message, tg_user.id, tg_user.full_name)


async def menu_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    role = callback.data.split(':', maxsplit=1)[1]
    await callback.message.answer('Главное меню:', reply_markup=role_menu_keyboard(role))
    await callback.answer()


async def customer_menu_handler(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split(':', maxsplit=1)[1]
    telegram_id = callback.from_user.id

    if action == 'book':
        await state.clear()
        role, user = await sync_to_async(_resolve_role_and_user, thread_sensitive=True)(telegram_id)
        tenants = await sync_to_async(_get_active_tenants_for_role, thread_sensitive=True)(role, user)
        if not tenants:
            await callback.message.answer('Нет доступных бизнесов для записи.')
            await callback.answer()
            return
        await state.set_state(BookingFlow.choosing_tenant)
        await callback.message.answer('Выберите бизнес:', reply_markup=await tenant_keyboard(tenants))
        await callback.answer()
        return

    if action == 'bookings':
        rows = await sync_to_async(_get_customer_bookings, thread_sensitive=True)(telegram_id)
        text = _format_booking_rows(rows)
        await callback.message.answer(text, reply_markup=main_menu_keyboard('customer'))
        await callback.answer()
        return

    if action == 'cancel_menu':
        rows = await sync_to_async(_get_customer_cancellable_bookings, thread_sensitive=True)(telegram_id)
        if not rows:
            await callback.message.answer('Нет записей для отмены.', reply_markup=main_menu_keyboard('customer'))
            await callback.answer()
            return
        await callback.message.answer('Выберите запись для отмены:', reply_markup=cancel_booking_keyboard(rows))
        await callback.answer()
        return


async def cancel_booking_handler(callback: CallbackQuery):
    booking_id = int(callback.data.split(':', maxsplit=1)[1])
    cancelled = await sync_to_async(_cancel_customer_booking, thread_sensitive=True)(callback.from_user.id, booking_id)
    if cancelled:
        await callback.message.answer('Запись отменена.', reply_markup=main_menu_keyboard('customer'))
    else:
        await callback.message.answer('Не удалось отменить запись.', reply_markup=main_menu_keyboard('customer'))
    await callback.answer()


async def superadmin_handler(callback: CallbackQuery):
    action = callback.data.split(':', maxsplit=1)[1]

    if action == 'tenants':
        tenants = await sync_to_async(_superadmin_tenants, thread_sensitive=True)()
        if not tenants:
            text = 'Бизнесов пока нет.'
        else:
            text = '\n'.join(
                [
                    f'{name} | active={active} | plan={plan} | bookings={count}'
                    for name, active, plan, count in tenants
                ]
            )
        await callback.message.answer(text, reply_markup=main_menu_keyboard(User.ROLE_SUPERADMIN))
        await callback.answer()
        return

    if action == 'today':
        rows = await sync_to_async(_superadmin_today_bookings, thread_sensitive=True)()
        if not rows:
            text = 'Сегодня записей нет.'
        else:
            lines = []
            for booking_id, tenant_name, customer_name, service_name, start_dt, status in rows:
                lines.append(
                    f'#{booking_id} | {tenant_name} | {customer_name} | {service_name} | '
                    f'{start_dt.astimezone().strftime("%H:%M")} | {status}'
                )
            text = '\n'.join(lines)
        await callback.message.answer(text, reply_markup=main_menu_keyboard(User.ROLE_SUPERADMIN))
        await callback.answer()
        return

    if action == 'stats':
        stats = await sync_to_async(_superadmin_stats, thread_sensitive=True)()
        text = (
            f"Tenants: {stats['tenants_total']} (active: {stats['tenants_active']})\n"
            f"Customers: {stats['customers']}\n"
            f"Bookings today: {stats['bookings_today']}\n"
            f"Future bookings: {stats['bookings_future']}"
        )
        await callback.message.answer(text, reply_markup=main_menu_keyboard(User.ROLE_SUPERADMIN))
        await callback.answer()


async def owner_handler(callback: CallbackQuery):
    action = callback.data.split(':', maxsplit=1)[1]
    role, user = await sync_to_async(_resolve_role_and_user, thread_sensitive=True)(callback.from_user.id)
    if role != User.ROLE_OWNER or not user or not user.tenant_id:
        await callback.message.answer('Доступ запрещен.')
        await callback.answer()
        return

    if action == 'services':
        services = await sync_to_async(_owner_services, thread_sensitive=True)(user.tenant_id)
        text = '\n'.join([f'{name} | {duration} мин | {price}' for name, duration, price in services]) if services else 'Услуг нет.'
        await callback.message.answer(text, reply_markup=main_menu_keyboard(User.ROLE_OWNER))
        await callback.answer()
        return

    if action == 'staff':
        staff_rows = await sync_to_async(_owner_staff, thread_sensitive=True)(user.tenant_id)
        text = '\n'.join([f'{name} | {phone or "-"}' for name, phone in staff_rows]) if staff_rows else 'Сотрудников нет.'
        await callback.message.answer(text, reply_markup=main_menu_keyboard(User.ROLE_OWNER))
        await callback.answer()
        return

    if action in {'today', 'upcoming'}:
        days = 1 if action == 'today' else 7
        rows = await sync_to_async(_owner_or_staff_bookings, thread_sensitive=True)(user.tenant_id, days)
        if not rows:
            text = 'Записей нет.'
        else:
            text = '\n'.join(
                [
                    f'#{booking_id} | {customer_name} | {service_name} | '
                    f'{start_dt.astimezone().strftime("%Y-%m-%d %H:%M")} | {status}'
                    for booking_id, customer_name, service_name, start_dt, status in rows
                ]
            )
        await callback.message.answer(text, reply_markup=main_menu_keyboard(User.ROLE_OWNER))
        await callback.answer()


async def staff_handler(callback: CallbackQuery):
    action = callback.data.split(':', maxsplit=1)[1]
    role, user = await sync_to_async(_resolve_role_and_user, thread_sensitive=True)(callback.from_user.id)
    if role != User.ROLE_STAFF or not user or not user.tenant_id:
        await callback.message.answer('Доступ запрещен.')
        await callback.answer()
        return

    if action in {'today', 'upcoming'}:
        days = 1 if action == 'today' else 7
        rows = await sync_to_async(_owner_or_staff_bookings, thread_sensitive=True)(user.tenant_id, days)
        if not rows:
            text = 'Записей нет.'
        else:
            text = '\n'.join(
                [
                    f'#{booking_id} | {customer_name} | {service_name} | '
                    f'{start_dt.astimezone().strftime("%Y-%m-%d %H:%M")} | {status}'
                    for booking_id, customer_name, service_name, start_dt, status in rows
                ]
            )
        await callback.message.answer(text, reply_markup=main_menu_keyboard(User.ROLE_STAFF))
        await callback.answer()


async def tenant_selected(callback: CallbackQuery, state: FSMContext):
    tenant_id = int(callback.data.split(':', maxsplit=1)[1])
    service_rows = await sync_to_async(_get_active_services, thread_sensitive=True)(tenant_id)

    if not service_rows:
        await callback.message.answer('Услуг в этом бизнесе пока нет.', reply_markup=main_menu_keyboard('customer'))
        await callback.answer()
        return

    await state.update_data(tenant_id=tenant_id)
    await state.set_state(BookingFlow.choosing_service)
    await callback.message.answer('Выберите услугу:', reply_markup=await service_keyboard(service_rows))
    await callback.answer()


async def service_selected(callback: CallbackQuery, state: FSMContext):
    service_id = int(callback.data.split(':', maxsplit=1)[1])
    data = await state.get_data()
    tenant_id = data.get('tenant_id')

    service_exists = await sync_to_async(
        Service.objects.filter(id=service_id, tenant_id=tenant_id, is_active=True).exists,
        thread_sensitive=True,
    )()
    if not service_exists:
        await callback.message.answer('Услуга не найдена.', reply_markup=main_menu_keyboard('customer'))
        await callback.answer()
        return

    await state.update_data(service_id=service_id)
    await state.set_state(BookingFlow.choosing_date)
    await callback.message.answer('Выберите дату:', reply_markup=date_keyboard())
    await callback.answer()


async def date_selected(callback: CallbackQuery, state: FSMContext):
    selected_date = callback.data.split(':', maxsplit=1)[1]
    data = await state.get_data()

    tenant = await sync_to_async(Tenant.objects.filter(id=data['tenant_id'], is_active=True).first, thread_sensitive=True)()
    service = await sync_to_async(Service.objects.filter(id=data['service_id'], is_active=True).first, thread_sensitive=True)()
    if tenant is None or service is None:
        await callback.message.answer('Ошибка сессии. Нажмите /start', reply_markup=main_menu_keyboard('customer'))
        await state.clear()
        await callback.answer()
        return

    day = date.fromisoformat(selected_date)
    slots = await sync_to_async(get_available_slots, thread_sensitive=True)(tenant, service, day)
    if not slots:
        await callback.message.answer('На выбранную дату свободных слотов нет, выберите другую дату.', reply_markup=date_keyboard())
        await callback.answer()
        return

    await state.update_data(selected_date=selected_date)
    await state.set_state(BookingFlow.choosing_slot)
    await callback.message.answer('Выберите время:', reply_markup=slot_keyboard(slots))
    await callback.answer()


async def slot_selected(callback: CallbackQuery, state: FSMContext):
    slot_raw = callback.data.split(':', maxsplit=1)[1]
    slot_dt = datetime.fromisoformat(slot_raw)
    if timezone.is_naive(slot_dt):
        slot_dt = timezone.make_aware(slot_dt, timezone.get_current_timezone())

    data = await state.get_data()
    customer = await sync_to_async(Customer.objects.filter(telegram_id=callback.from_user.id).first, thread_sensitive=True)()
    tenant = await sync_to_async(Tenant.objects.filter(id=data['tenant_id'], is_active=True).first, thread_sensitive=True)()
    service = await sync_to_async(
        Service.objects.filter(id=data['service_id'], tenant_id=data['tenant_id'], is_active=True).first,
        thread_sensitive=True,
    )()

    if customer is None or tenant is None or service is None:
        await callback.message.answer('Ошибка сессии. Нажмите /start', reply_markup=main_menu_keyboard('customer'))
        await state.clear()
        await callback.answer()
        return

    day_slots = await sync_to_async(get_available_slots, thread_sensitive=True)(tenant, service, slot_dt.date())
    if not any(s == slot_dt for s in day_slots):
        await callback.message.answer('Слот уже занят. Выберите другое время через /start', reply_markup=main_menu_keyboard('customer'))
        await state.clear()
        await callback.answer()
        return

    booking = await sync_to_async(_create_booking, thread_sensitive=True)(tenant, customer, service, slot_dt)

    await callback.message.answer(
        'Запись подтверждена:\n'
        f'Бизнес: {tenant.name}\n'
        f'Услуга: {service.name}\n'
        f'Дата/время: {booking.start_datetime.astimezone().strftime("%Y-%m-%d %H:%M")}\n'
        f'Номер записи: {booking.id}',
        reply_markup=main_menu_keyboard('customer'),
    )
    await callback.answer()
    await state.clear()


async def main():
    token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    if not token:
        raise RuntimeError('TELEGRAM_BOT_TOKEN is required')

    bot = Bot(token=token)
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.register(start_handler, CommandStart())

    dp.callback_query.register(menu_handler, F.data.startswith('menu:'))

    dp.callback_query.register(customer_menu_handler, F.data.startswith('customer:'))
    dp.callback_query.register(cancel_booking_handler, F.data.startswith('cancel:'))

    dp.callback_query.register(superadmin_handler, F.data.startswith('super:'))
    dp.callback_query.register(owner_handler, F.data.startswith('owner:'))
    dp.callback_query.register(staff_handler, F.data.startswith('staff:'))

    dp.callback_query.register(tenant_selected, BookingFlow.choosing_tenant, F.data.startswith('tenant:'))
    dp.callback_query.register(service_selected, BookingFlow.choosing_service, F.data.startswith('service:'))
    dp.callback_query.register(date_selected, BookingFlow.choosing_date, F.data.startswith('date:'))
    dp.callback_query.register(slot_selected, BookingFlow.choosing_slot, F.data.startswith('slot:'))

    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
