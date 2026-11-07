from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'order',
        'payment_method',
        'status',
        'amount',
        'phone_number',
        'mpesa_receipt_number',
        'result_code',
        'created_at',
    )
    list_filter = ('payment_method', 'status', 'created_at')
    search_fields = ('order__id', 'transaction_id', 'checkout_request_id', 'mpesa_receipt_number', 'phone_number')
    readonly_fields = ('created_at', 'raw_callback')
    fieldsets = (
        (
            'Payment',
            {
                'fields': (
                    'order',
                    'payment_method',
                    'status',
                    'amount',
                    'phone_number',
                    'transaction_id',
                )
            },
        ),
        (
            'M-Pesa Details',
            {
                'fields': (
                    'merchant_request_id',
                    'checkout_request_id',
                    'result_code',
                    'result_desc',
                    'mpesa_receipt_number',
                    'raw_callback',
                )
            },
        ),
        ('Metadata', {'fields': ('created_at',)}),
    )
