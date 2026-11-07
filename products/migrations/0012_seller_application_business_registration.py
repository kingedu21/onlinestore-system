from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0011_seller_application_id_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='sellerapplication',
            name='business_registration',
            field=models.CharField(max_length=60),
        ),
    ]
