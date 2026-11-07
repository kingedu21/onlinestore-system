from django.conf import settings
from django.db import models


class Category(models.Model):
    # Product grouping for catalog navigation.
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = 'Categories'

    def __str__(self) -> str:
        return self.name


class SubCategory(models.Model):
    # Sub-group under a category (e.g., Electronics -> Phones).
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)

    class Meta:
        unique_together = ('category', 'name')
        verbose_name_plural = 'Subcategories'

    def __str__(self) -> str:
        return f'{self.category.name} - {self.name}'


class Seller(models.Model):
    # Third-party or individual seller profile.
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='seller_profile')
    store_name = models.CharField(max_length=150, default='', blank=True)
    name = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    is_suspicious = models.BooleanField(default=False)
    suspicious_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.store_name


class SellerApplication(models.Model):
    # Application to become a seller (admin approval required).
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='seller_applications')
    full_name = models.CharField(max_length=150)
    business_name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=30)
    email = models.EmailField()
    business_address = models.TextField()
    mpesa_number = models.CharField(max_length=30)
    business_registration = models.CharField(max_length=60)
    id_number = models.CharField(max_length=30)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f'{self.full_name} - {self.business_name}'


class Product(models.Model):
    # Core catalog item with pricing and stock.
    CONDITION_NEW = 'new'
    CONDITION_USED = 'used'
    CONDITION_REFURBISHED = 'refurbished'
    CONDITION_CHOICES = [
        (CONDITION_NEW, 'New'),
        (CONDITION_USED, 'Second Hand'),
        (CONDITION_REFURBISHED, 'Refurbished'),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    subcategory = models.ForeignKey(SubCategory, on_delete=models.PROTECT, related_name='products', null=True, blank=True)
    seller = models.ForeignKey(Seller, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    is_approved = models.BooleanField(default=True)
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default=CONDITION_NEW)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name


class ProductImage(models.Model):
    # Additional product gallery images.
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f'Image for {self.product_id}'


class Variation(models.Model):
    # Product variation (e.g., Size M, Color Red).
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variations')
    name = models.CharField(max_length=50)
    value = models.CharField(max_length=50)
    price_modifier = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('product', 'name', 'value')

    def __str__(self) -> str:
        return f'{self.product.name} - {self.name}: {self.value}'


class Review(models.Model):
    # Customer review and rating for a product.
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('product', 'user')

    def __str__(self) -> str:
        return f'{self.product} - {self.rating}'


class Wishlist(models.Model):
    # Saved products per user.
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='wishlist_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlisted_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')

    def __str__(self) -> str:
        return f'{self.user} - {self.product}'


class HelpMessage(models.Model):
    # Help center contact messages.
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=150)
    email = models.EmailField()
    message = models.TextField()
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.name} - {self.email}'
