from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('payments', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='phone_number',
            field=models.CharField(blank=True, max_length=30),
        ),
        migrations.AddField(
            model_name='payment',
            name='amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='payment',
            name='merchant_request_id',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='payment',
            name='checkout_request_id',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='payment',
            name='result_code',
            field=models.CharField(blank=True, max_length=10),
        ),
        migrations.AddField(
            model_name='payment',
            name='result_desc',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='payment',
            name='mpesa_receipt_number',
            field=models.CharField(blank=True, max_length=60),
        ),
        migrations.AddField(
            model_name='payment',
            name='raw_callback',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
