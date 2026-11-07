from django.conf import settings
from django.db import models
from django.utils import timezone

from products.models import Product
from accounts.models import Notification


class Order(models.Model):
    # Customer order with status tracking.
    STATUS_PENDING = 'pending'
    STATUS_PROCESSING = 'processing'
    STATUS_SHIPPED = 'shipped'
    STATUS_OUT_FOR_DELIVERY = 'out_for_delivery'
    STATUS_DELIVERED = 'delivered'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_SHIPPED, 'Shipped'),
        (STATUS_OUT_FOR_DELIVERY, 'Out for Delivery'),
        (STATUS_DELIVERED, 'Delivered'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    PAYMENT_PENDING = 'pending'
    PAYMENT_PAID = 'paid'
    PAYMENT_FAILED = 'failed'
    PAYMENT_STATUS_CHOICES = [
        (PAYMENT_PENDING, 'Pending'),
        (PAYMENT_PAID, 'Paid'),
        (PAYMENT_FAILED, 'Failed'),
    ]

    METHOD_MPESA = 'mpesa'
    METHOD_CARD = 'card'
    METHOD_CASH = 'cash'
    PAYMENT_METHOD_CHOICES = [
        (METHOD_MPESA, 'M-Pesa'),
        (METHOD_CARD, 'Card'),
        (METHOD_CASH, 'Cash on Delivery'),
    ]

    DELIVERY_PICKUP = 'pickup'
    DELIVERY_DOOR = 'door'
    DELIVERY_METHOD_CHOICES = [
        (DELIVERY_PICKUP, 'Pickup Station'),
        (DELIVERY_DOOR, 'Door Delivery'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_method = models.CharField(max_length=20, choices=DELIVERY_METHOD_CHOICES, default=DELIVERY_PICKUP)
    delivery_county = models.CharField(max_length=60, blank=True)
    delivery_town = models.CharField(max_length=60, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default=METHOD_CASH)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default=PAYMENT_PENDING)
    coupon_code = models.CharField(max_length=50, blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f'Order {self.id} - {self.user}'

    def save(self, *args, **kwargs):
        previous_status = None
        previous_payment = None
        if self.pk:
            previous = Order.objects.filter(pk=self.pk).values('status', 'payment_status').first()
            if previous:
                previous_status = previous.get('status')
                previous_payment = previous.get('payment_status')
        super().save(*args, **kwargs)
        if previous_status != self.status:
            OrderTracking.objects.create(order=self, status=self.status)
            if self.status in [Order.STATUS_SHIPPED, Order.STATUS_OUT_FOR_DELIVERY, Order.STATUS_DELIVERED]:
                Notification.objects.create(
                    user=self.user,
                    message=f'Your order #{self.id} status is now {self.get_status_display()}.',
                )
        if previous_payment != self.payment_status and self.payment_status == Order.PAYMENT_PAID:
            Receipt.objects.get_or_create(order=self, defaults={'amount_paid': self.total_price, 'payment_method': self.payment_method})
            if hasattr(self, 'invoice'):
                self.invoice.payment_status = self.payment_status
                self.invoice.save(update_fields=['payment_status'])
            Notification.objects.create(
                user=self.user,
                message=f'Payment received for order #{self.id}.',
            )


class Invoice(models.Model):
    # Invoice generated when an order is created.
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='invoice')
    invoice_number = models.CharField(max_length=30, unique=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(max_length=20, choices=Order.PAYMENT_STATUS_CHOICES, default=Order.PAYMENT_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.invoice_number and self.order_id:
            self.invoice_number = f'INV-{self.order_id:06d}'
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.invoice_number


class Receipt(models.Model):
    # Receipt generated when payment is marked as paid.
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='receipt')
    receipt_number = models.CharField(max_length=30, unique=True, blank=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=Order.PAYMENT_METHOD_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.receipt_number and self.order_id:
            self.receipt_number = f'RCT-{self.order_id:06d}'
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.receipt_number


class OrderTracking(models.Model):
    # Order status history for customer tracking.
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='tracking_entries')
    status = models.CharField(max_length=30, choices=Order.STATUS_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self) -> str:
        return f'{self.order_id} - {self.status}'


class OrderItem(models.Model):
    # Line item with price snapshot at time of purchase.
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='order_items')
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    product_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    seller_earning = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    @property
    def subtotal(self):
        return self.price * self.quantity

    def __str__(self) -> str:
        return f'{self.product} x {self.quantity}'


class Commission(models.Model):
    # Platform commission record per order item.
    PAYOUT_PENDING = 'pending'
    PAYOUT_PAID = 'paid'
    PAYOUT_STATUS_CHOICES = [
        (PAYOUT_PENDING, 'Pending'),
        (PAYOUT_PAID, 'Paid'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='commissions')
    order_item = models.OneToOneField(OrderItem, on_delete=models.CASCADE, related_name='commission')
    seller = models.ForeignKey('products.Seller', on_delete=models.SET_NULL, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2)
    seller_earning = models.DecimalField(max_digits=10, decimal_places=2)
    seller_payout_status = models.CharField(max_length=20, choices=PAYOUT_STATUS_CHOICES, default=PAYOUT_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f'Commission {self.id} - Order {self.order_id}'


class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount_percentage = models.PositiveSmallIntegerField()
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    active = models.BooleanField(default=True)

    def is_valid(self):
        now = timezone.now()
        return self.active and self.valid_from <= now <= self.valid_to

    def __str__(self) -> str:
        return self.code
