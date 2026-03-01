from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
        ('services', '0001_initial'),
        ('tenants', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Booking',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_datetime', models.DateTimeField()),
                ('end_datetime', models.DateTimeField()),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('confirmed', 'Confirmed'), ('cancelled', 'Cancelled'), ('completed', 'Completed')], default='pending', max_length=16)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('comment', models.TextField(blank=True)),
                ('customer', models.ForeignKey(on_delete=models.CASCADE, related_name='bookings', to='accounts.customer')),
                ('service', models.ForeignKey(on_delete=models.PROTECT, related_name='bookings', to='services.service')),
                ('staff', models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name='bookings', to='services.staff')),
                ('tenant', models.ForeignKey(on_delete=models.CASCADE, related_name='bookings', to='tenants.tenant')),
            ],
            options={
                'ordering': ['start_datetime'],
                'indexes': [
                    models.Index(fields=['tenant', 'start_datetime'], name='bookings_bo_tenant__651c5d_idx'),
                    models.Index(fields=['status', 'start_datetime'], name='bookings_bo_status_d505ba_idx'),
                ],
            },
        ),
    ]
