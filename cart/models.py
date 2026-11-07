from decimal import Decimal

from django.conf import settings
from django.db import models

from products.models import Product, Variation


class Cart(models.Model):
    # One active cart per user.
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='carts')
    created_at = models.DateTimeField(auto_now_add=True)

    def add_product(self, product: Product, quantity: int = 1, variation: Variation | None = None) -> None:
        item, created = CartItem.objects.get_or_create(cart=self, product=product, variation=variation)
        item.quantity = item.quantity + quantity if not created else quantity
        item.save(update_fields=['quantity'])

    def update_item(self, product: Product, quantity: int, variation: Variation | None = None) -> None:
        item = CartItem.objects.filter(cart=self, product=product, variation=variation).first()
        if not item:
            return
        if quantity <= 0:
            item.delete()
            return
        item.quantity = quantity
        item.save(update_fields=['quantity'])

    def remove_product(self, product: Product, variation: Variation | None = None) -> None:
        CartItem.objects.filter(cart=self, product=product, variation=variation).delete()

    @property
    def total_price(self) -> Decimal:
        return sum((item.subtotal for item in self.items.select_related('product')), Decimal('0.00'))

    def __str__(self) -> str:
        return f'Cart {self.id} for {self.user}'


class CartItem(models.Model):
    # Snapshot of a product and quantity inside a cart.
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='cart_items')
    variation = models.ForeignKey(Variation, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('cart', 'product', 'variation')

    @property
    def subtotal(self) -> Decimal:
        return self.product.price * self.quantity

    def __str__(self) -> str:
        return f'{self.product} x {self.quantity}'
