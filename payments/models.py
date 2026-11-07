from django.db import models

from orders.models import Order


class Payment(models.Model):
    # Payment record prepared for later M-Pesa integration.
    METHOD_MPESA = 'mpesa'
    METHOD_CARD = 'card'
    METHOD_CASH = 'cash'
    METHOD_CHOICES = [
        (METHOD_MPESA, 'M-Pesa'),
        (METHOD_CARD, 'Card'),
        (METHOD_CASH, 'Cash'),
    ]

    STATUS_PENDING = 'pending'
    STATUS_SUCCESS = 'success'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_SUCCESS, 'Success'),
        (STATUS_FAILED, 'Failed'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    payment_method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    transaction_id = models.CharField(max_length=120, blank=True)
    phone_number = models.CharField(max_length=30, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    merchant_request_id = models.CharField(max_length=120, blank=True)
    checkout_request_id = models.CharField(max_length=120, blank=True)
    result_code = models.CharField(max_length=10, blank=True)
    result_desc = models.CharField(max_length=255, blank=True)
    mpesa_receipt_number = models.CharField(max_length=60, blank=True)
    raw_callback = models.JSONField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        previous_status = None
        if self.pk:
            previous_status = Payment.objects.filter(pk=self.pk).values_list('status', flat=True).first()

        super().save(*args, **kwargs)

        if previous_status == self.status:
            return

        if self.status == Payment.STATUS_SUCCESS:
            update_fields = ['payment_status']
            if self.order.payment_method != self.payment_method:
                self.order.payment_method = self.payment_method
                update_fields.append('payment_method')
            self.order.payment_status = Order.PAYMENT_PAID
            self.order.save(update_fields=update_fields)
        elif self.status == Payment.STATUS_FAILED:
            self.order.payment_status = Order.PAYMENT_FAILED
            self.order.save(update_fields=['payment_status'])

    def __str__(self) -> str:
        return f'Payment {self.id} for order {self.order_id}'
