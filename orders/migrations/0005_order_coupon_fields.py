from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0004_order_delivery_county_order_delivery_method_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='coupon_code',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name='order',
            name='discount_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]
