# Generated by Django 3.2 on 2022-06-22 11:56

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('profile', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='FreezeBalance',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('eosish', models.DecimalField(decimal_places=0, max_digits=78)),
                ('wish', models.DecimalField(decimal_places=0, max_digits=78)),
                ('tronish', models.DecimalField(decimal_places=0, max_digits=78)),
                ('bwish', models.DecimalField(decimal_places=0, max_digits=78)),
            ],
        ),
        migrations.CreateModel(
            name='InternalPayment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('delta', models.DecimalField(decimal_places=0, max_digits=78)),
                ('tx_hash', models.CharField(default='', max_length=66, null=True)),
                ('datetime', models.DateTimeField(auto_now_add=True)),
                ('original_currency', models.CharField(default='', max_length=66, null=True)),
                ('original_delta', models.CharField(default='', max_length=66, null=True)),
                ('fake', models.BooleanField(default=False)),
                ('site', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='profile.subsite')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='BTCAccount',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('address', models.CharField(max_length=50)),
                ('used', models.BooleanField(default=False)),
                ('balance', models.IntegerField(default=0)),
                ('user', models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
