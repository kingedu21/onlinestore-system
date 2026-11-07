from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    # Custom user profile fields and role control.
    ROLE_ADMIN = 'admin'
    ROLE_SELLER = 'seller'
    ROLE_CUSTOMER = 'customer'
    ROLE_CHOICES = [
        (ROLE_ADMIN, 'Admin'),
        (ROLE_SELLER, 'Seller'),
        (ROLE_CUSTOMER, 'Customer'),
    ]

    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_CUSTOMER)
    must_change_password = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.get_username()

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower()
            if not self.username:
                self.username = self.email
        super().save(*args, **kwargs)


class Notification(models.Model):
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'Notification {self.id} for {self.user}'
