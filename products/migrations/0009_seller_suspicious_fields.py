from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0008_productimage'),
    ]

    operations = [
        migrations.AddField(
            model_name='seller',
            name='is_suspicious',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='seller',
            name='suspicious_reason',
            field=models.TextField(blank=True),
        ),
    ]
