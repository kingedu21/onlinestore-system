from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0009_seller_suspicious_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='SellerApplication',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('full_name', models.CharField(max_length=150)),
                ('business_name', models.CharField(max_length=150)),
                ('phone_number', models.CharField(max_length=30)),
                ('email', models.EmailField(max_length=254)),
                ('business_address', models.TextField()),
                ('mpesa_number', models.CharField(max_length=30)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='seller_applications', to='accounts.user')),
            ],
        ),
    ]
