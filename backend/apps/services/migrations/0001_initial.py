from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('tenants', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Service',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('duration_minutes', models.PositiveIntegerField()),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('is_active', models.BooleanField(default=True)),
                ('tenant', models.ForeignKey(on_delete=models.CASCADE, related_name='services', to='tenants.tenant')),
            ],
            options={
                'ordering': ['name'],
                'indexes': [models.Index(fields=['tenant', 'is_active'], name='services_se_tenant__8fbccf_idx')],
            },
        ),
        migrations.CreateModel(
            name='Staff',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('phone', models.CharField(blank=True, max_length=32)),
                ('is_active', models.BooleanField(default=True)),
                ('tenant', models.ForeignKey(on_delete=models.CASCADE, related_name='staff_members', to='tenants.tenant')),
            ],
            options={
                'ordering': ['name'],
                'indexes': [models.Index(fields=['tenant', 'is_active'], name='services_st_tenant__f6f634_idx')],
            },
        ),
        migrations.CreateModel(
            name='WorkingHours',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('weekday', models.PositiveSmallIntegerField()),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('is_working_day', models.BooleanField(default=True)),
                ('tenant', models.ForeignKey(on_delete=models.CASCADE, related_name='working_hours', to='tenants.tenant')),
            ],
            options={
                'ordering': ['tenant', 'weekday'],
                'unique_together': {('tenant', 'weekday')},
            },
        ),
    ]
