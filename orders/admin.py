from django.contrib import admin

from .models import Commission, Coupon, Invoice, Order, OrderItem, OrderTracking, Receipt


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


class OrderTrackingInline(admin.TabularInline):
    model = OrderTracking
    extra = 0
    readonly_fields = ('status', 'timestamp')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'total_price', 'status', 'payment_status', 'payment_method', 'created_at')
    list_filter = ('status', 'payment_status', 'payment_method')
    inlines = [OrderItemInline, OrderTrackingInline]
    actions = [
        'mark_processing',
        'mark_shipped',
        'mark_out_for_delivery',
        'mark_delivered',
        'mark_completed_paid',
        'mark_cancelled',
    ]

    def _update_status(self, request, queryset, status):
        for order in queryset:
            order.status = status
            order.save(update_fields=['status'])

    def mark_processing(self, request, queryset):
        self._update_status(request, queryset, Order.STATUS_PROCESSING)
    mark_processing.short_description = 'Mark selected orders as Processing'

    def mark_shipped(self, request, queryset):
        self._update_status(request, queryset, Order.STATUS_SHIPPED)
    mark_shipped.short_description = 'Mark selected orders as Shipped'

    def mark_out_for_delivery(self, request, queryset):
        self._update_status(request, queryset, Order.STATUS_OUT_FOR_DELIVERY)
    mark_out_for_delivery.short_description = 'Mark selected orders as Out for Delivery'

    def mark_delivered(self, request, queryset):
        self._update_status(request, queryset, Order.STATUS_DELIVERED)
    mark_delivered.short_description = 'Mark selected orders as Delivered'

    def mark_completed_paid(self, request, queryset):
        for order in queryset:
            order.status = Order.STATUS_COMPLETED
            order.payment_status = Order.PAYMENT_PAID
            order.save(update_fields=['status', 'payment_status'])
    mark_completed_paid.short_description = 'Mark selected orders as Completed and Paid'

    def mark_cancelled(self, request, queryset):
        self._update_status(request, queryset, Order.STATUS_CANCELLED)
    mark_cancelled.short_description = 'Mark selected orders as Cancelled'


@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'seller', 'commission_amount', 'seller_earning', 'seller_payout_status', 'created_at')
    list_filter = ('seller', 'seller_payout_status')
    actions = ['mark_payout_paid']

    def mark_payout_paid(self, request, queryset):
        queryset.update(seller_payout_status=Commission.PAYOUT_PAID)
    mark_payout_paid.short_description = 'Mark selected payouts as Paid'


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'order', 'total_amount', 'payment_status', 'created_at')
    list_filter = ('payment_status',)


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ('receipt_number', 'order', 'amount_paid', 'payment_method', 'created_at')
    list_filter = ('payment_method',)


@admin.register(OrderTracking)
class OrderTrackingAdmin(admin.ModelAdmin):
    list_display = ('order', 'status', 'timestamp')


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_percentage', 'valid_from', 'valid_to', 'active')
    list_filter = ('active',)
    search_fields = ('code',)
