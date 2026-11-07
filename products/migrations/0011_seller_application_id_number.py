from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0010_seller_application'),
    ]

    operations = [
        migrations.AddField(
            model_name='sellerapplication',
            name='id_number',
            field=models.CharField(max_length=30),
        ),
    ]
