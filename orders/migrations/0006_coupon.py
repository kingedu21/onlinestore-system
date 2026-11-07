from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0005_order_coupon_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='Coupon',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=50, unique=True)),
                ('discount_percentage', models.PositiveSmallIntegerField()),
                ('valid_from', models.DateTimeField()),
                ('valid_to', models.DateTimeField()),
                ('active', models.BooleanField(default=True)),
            ],
        ),
    ]
