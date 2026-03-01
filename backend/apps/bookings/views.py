from datetime import date

from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.services.models import Service
from apps.tenants.models import Tenant
from .models import Booking
from .serializers import BookingCreateSerializer, BookingSerializer
from .services import get_available_slots


class BookingCreateAPIView(generics.CreateAPIView):
    serializer_class = BookingCreateSerializer
    permission_classes = [permissions.AllowAny]


class TenantBookingListAPIView(generics.ListAPIView):
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        tenant_id = self.kwargs['tenant_id']
        user = self.request.user
        qs = Booking.objects.filter(tenant_id=tenant_id).select_related('customer', 'service', 'staff', 'tenant')
        if user.role == 'superadmin':
            return qs
        if user.tenant_id != tenant_id:
            return Booking.objects.none()
        return qs


class AvailableSlotsAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, tenant_id):
        service_id = request.query_params.get('service_id')
        date_str = request.query_params.get('date')

        if not service_id or not date_str:
            return Response({'detail': 'service_id and date are required.'}, status=status.HTTP_400_BAD_REQUEST)

        target_date: date | None = parse_date(date_str)
        if not target_date:
            return Response({'detail': 'Invalid date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

        tenant = get_object_or_404(Tenant, pk=tenant_id, is_active=True)
        service = get_object_or_404(Service, pk=service_id, tenant=tenant, is_active=True)

        slots = get_available_slots(tenant, service, target_date)
        return Response({'slots': [s.isoformat() for s in slots]})
