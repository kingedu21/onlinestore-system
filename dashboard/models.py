from django.db import models


class PlatformSettings(models.Model):
    # Singleton-style settings for marketplace.
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=10)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f'Platform Settings ({self.commission_rate}%)'
