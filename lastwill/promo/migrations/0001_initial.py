# Generated by Django 3.2 on 2022-06-22 11:56

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Promo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start', models.DateField(default=None, null=True)),
                ('stop', models.DateField(default=None, null=True)),
                ('use_count', models.IntegerField(default=0)),
                ('use_count_max', models.IntegerField(default=None, null=True)),
                ('promo_str', models.CharField(max_length=32, unique=True)),
                ('referral_bonus_usd', models.IntegerField(default=0)),
                ('reusable', models.BooleanField(default=False)),
                ('user', models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='User2Promo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('contract_id', models.IntegerField(default=0)),
                ('promo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='promo.promo')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Promo2ContractType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('contract_type', models.IntegerField()),
                ('discount', models.IntegerField()),
                ('promo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='promo.promo')),
            ],
        ),
    ]
