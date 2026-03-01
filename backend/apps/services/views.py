from rest_framework import generics, permissions

from .models import Service
from .serializers import ServiceSerializer


class ServiceListAPIView(generics.ListAPIView):
    serializer_class = ServiceSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        tenant_id = self.kwargs['tenant_id']
        return Service.objects.filter(tenant_id=tenant_id, is_active=True).select_related('tenant')
