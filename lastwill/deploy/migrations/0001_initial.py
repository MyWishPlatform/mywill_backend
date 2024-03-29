# Generated by Django 3.2 on 2022-06-22 11:56

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Network',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_index=True, max_length=128)),
            ],
        ),
        migrations.CreateModel(
            name='DeployAddress',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('address', models.CharField(max_length=50)),
                ('locked_by', models.IntegerField(default=None, null=True)),
                ('network', models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='deploy.network')),
            ],
        ),
    ]
