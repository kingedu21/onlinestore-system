from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.conf import settings
from django.views.decorators.http import require_POST

from cart.models import Cart
from accounts.models import Notification
from dashboard.models import PlatformSettings
from orders.models import Commission

from payments.models import Payment
from payments.services import MpesaError, is_mpesa_configured, normalize_phone_number, stk_push

from .models import Coupon, Invoice, Order, OrderItem, Receipt


def _get_user_cart(user):
    # Ensure each user has a cart.
    cart, _created = Cart.objects.get_or_create(user=user)
    return cart


def _compute_shipping_fee(county: str, method: str) -> Decimal:
    county_distance_km = {
        "Nairobi": 5,
        "Kiambu": 20,
        "Kajiado": 40,
        "Machakos": 60,
        "Murang'a": 80,
        "Nyandarua": 140,
        "Nyeri": 150,
        "Kirinyaga": 120,
        "Embu": 140,
        "Tharaka-Nithi": 190,
        "Meru": 220,
        "Laikipia": 210,
        "Nakuru": 160,
        "Narok": 150,
        "Bomet": 240,
        "Kericho": 260,
        "Nandi": 300,
        "Uasin Gishu": 310,
        "Trans Nzoia": 320,
        "Bungoma": 380,
        "Kakamega": 350,
        "Vihiga": 350,
        "Busia": 430,
        "Siaya": 380,
        "Kisumu": 350,
        "Homa Bay": 370,
        "Migori": 420,
        "Kisii": 330,
        "Nyamira": 340,
        "Baringo": 280,
        "Elgeyo-Marakwet": 290,
        "West Pokot": 420,
        "Samburu": 360,
        "Turkana": 650,
        "Isiolo": 280,
        "Marsabit": 560,
        "Mandera": 760,
        "Wajir": 520,
        "Garissa": 360,
        "Tana River": 450,
        "Lamu": 500,
        "Kilifi": 480,
        "Mombasa": 485,
        "Kwale": 520,
        "Taita-Taveta": 350,
        "Kitui": 160,
        "Makueni": 150,
    }
    km = county_distance_km.get(county, 50)
    per_km = Decimal('1')
    base = Decimal('100') if method == Order.DELIVERY_DOOR else Decimal('60')
    return base + (per_km * Decimal(km))


@login_required
def checkout(request):
    # Convert cart items to a new order.
    if request.user.role != 'customer':
        messages.error(request, 'Admins and sellers cannot place orders.')
        return redirect('home')
    cart = _get_user_cart(request.user)
    items = cart.items.select_related('product')
    shipping_fee = Decimal('0.00')
    delivery_method = request.session.get('delivery_method', Order.DELIVERY_PICKUP)
    delivery_county = request.session.get('delivery_county', '')
    delivery_town = request.session.get('delivery_town', '')

    if not delivery_county:
        return redirect('delivery_confirm')
    if delivery_county:
        shipping_fee = _compute_shipping_fee(delivery_county, delivery_method)

    mpesa_phone = request.user.phone if request.user.is_authenticated else ''
    error_message = ''

    applied_coupon = None
    discount_amount = Decimal('0.00')

    if request.method == 'POST':
        if not items.exists():
            return redirect('view_cart')
        payment_method = request.POST.get('payment_method', Payment.METHOD_CASH)
        mpesa_phone = request.POST.get('mpesa_phone', '').strip() or mpesa_phone
        if payment_method == Order.METHOD_MPESA:
            if not is_mpesa_configured():
                error_message = 'M-Pesa is not configured yet. Please choose another payment method.'
            else:
                mpesa_phone = normalize_phone_number(mpesa_phone)
                if not mpesa_phone:
                    error_message = 'Enter a valid M-Pesa phone number (e.g. 07XXXXXXXX).'
        if error_message:
            return render(
                request,
                'orders/checkout.html',
                {
                    'cart': cart,
                    'items': items,
                    'shipping_fee': shipping_fee,
                    'delivery_method': delivery_method,
                    'delivery_county': delivery_county,
                    'delivery_town': delivery_town,
                    'error': error_message,
                    'mpesa_phone': mpesa_phone,
                    'coupon_code': request.POST.get('coupon_code', '').strip(),
                    'cart_subtotal': cart.total_price,
                    'discount_amount': Decimal('0.00'),
                    'order_total_preview': cart.total_price + shipping_fee,
                },
            )

        if payment_method in [Order.METHOD_CASH, Order.METHOD_MPESA]:
            payment_status = Order.PAYMENT_PENDING
        else:
            payment_status = Order.PAYMENT_PAID

        cart_total = Decimal('0.00')
        for item in items:
            if item.variation:
                if item.variation.stock < item.quantity:
                    messages.error(request, f'Insufficient stock for {item.product.name} ({item.variation.name}: {item.variation.value}).')
                    return redirect('view_cart')
            else:
                if item.product.stock < item.quantity:
                    messages.error(request, f'Insufficient stock for {item.product.name}.')
                    return redirect('view_cart')
            cart_total += item.product.price * item.quantity
        coupon_code = request.POST.get('coupon_code', '').strip()
        if coupon_code:
            coupon = Coupon.objects.filter(code__iexact=coupon_code).first()
            if not coupon or not coupon.is_valid():
                error_message = 'Invalid or expired coupon code.'
                return render(
                    request,
                    'orders/checkout.html',
                    {
                        'cart': cart,
                        'items': items,
                        'shipping_fee': shipping_fee,
                        'delivery_method': delivery_method,
                        'delivery_county': delivery_county,
                        'delivery_town': delivery_town,
                        'error': error_message,
                        'mpesa_phone': mpesa_phone,
                        'coupon_code': coupon_code,
                    },
                )
            applied_coupon = coupon
            discount_amount = (cart_total * Decimal(coupon.discount_percentage) / Decimal('100')).quantize(Decimal('0.01'))

        order_total = cart_total + shipping_fee - discount_amount

        try:
            with transaction.atomic():
                if request.user.role != 'customer':
                    raise PermissionDenied('Only customers can create orders.')
                order = Order.objects.create(
                    user=request.user,
                    status=Order.STATUS_PENDING,
                    payment_method=payment_method,
                    payment_status=payment_status,
                    shipping_fee=shipping_fee,
                    delivery_method=delivery_method,
                    delivery_county=delivery_county,
                    delivery_town=delivery_town,
                    coupon_code=applied_coupon.code if applied_coupon else '',
                    discount_amount=discount_amount,
                )
                for item in items:
                    line_total = item.product.price * item.quantity
                    settings_obj = PlatformSettings.objects.first()
                    commission_rate = settings_obj.commission_rate if settings_obj else Decimal(settings.COMMISSION_RATE)
                    commission_amount = (line_total * commission_rate) / Decimal('100')
                    seller_earning = line_total - commission_amount
                    order_item = OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        quantity=item.quantity,
                        price=item.product.price,
                        product_price=item.product.price,
                        commission_amount=commission_amount,
                        seller_earning=seller_earning,
                    )
                    if item.variation:
                        item.variation.stock = max(0, item.variation.stock - item.quantity)
                        item.variation.save(update_fields=['stock'])
                    item.product.stock = max(0, item.product.stock - item.quantity)
                    item.product.save(update_fields=['stock'])
                    Commission.objects.create(
                        order=order,
                        order_item=order_item,
                        seller=item.product.seller,
                        product=item.product,
                        commission_amount=commission_amount,
                        seller_earning=seller_earning,
                    )
                order.total_price = order_total
                order.save(update_fields=['total_price', 'shipping_fee', 'payment_status', 'payment_method', 'coupon_code', 'discount_amount'])
                Invoice.objects.get_or_create(
                    order=order,
                    defaults={'total_amount': order.total_price, 'payment_status': order.payment_status},
                )

                if payment_method == Order.METHOD_MPESA:
                    account_reference = f'{settings.MPESA_ACCOUNT_REFERENCE} #{order.id}'
                    transaction_desc = settings.MPESA_TRANSACTION_DESC
                    response = stk_push(mpesa_phone, order.total_price, account_reference, transaction_desc)
                    response_code = str(response.get('ResponseCode', ''))
                    if response_code != '0':
                        raise MpesaError(response.get('ResponseDescription', 'M-Pesa STK push failed.'))
                    checkout_request_id = response.get('CheckoutRequestID', '')
                    merchant_request_id = response.get('MerchantRequestID', '')
                    Payment.objects.create(
                        order=order,
                        payment_method=payment_method,
                        status=Payment.STATUS_PENDING,
                        transaction_id=checkout_request_id or '',
                        checkout_request_id=checkout_request_id or '',
                        merchant_request_id=merchant_request_id or '',
                        phone_number=mpesa_phone,
                        amount=order.total_price,
                    )
                else:
                    payment_record_status = Payment.STATUS_SUCCESS if payment_status == Order.PAYMENT_PAID else Payment.STATUS_PENDING
                    Payment.objects.create(order=order, payment_method=payment_method, status=payment_record_status)

                items.delete()
                Notification.objects.create(
                    user=request.user,
                    message=f'Your order #{order.id} has been placed successfully.',
                )
        except MpesaError as exc:
            return render(
                request,
                'orders/checkout.html',
                {
                    'cart': cart,
                    'items': items,
                    'shipping_fee': shipping_fee,
                    'delivery_method': delivery_method,
                    'delivery_county': delivery_county,
                    'delivery_town': delivery_town,
                    'error': str(exc),
                    'mpesa_phone': mpesa_phone,
                    'coupon_code': request.POST.get('coupon_code', '').strip(),
                    'cart_subtotal': cart_total,
                    'discount_amount': discount_amount,
                    'order_total_preview': cart_total + shipping_fee - discount_amount,
                },
            )

        return redirect('order_success', order_id=order.id)

    return render(
        request,
        'orders/checkout.html',
        {
            'cart': cart,
            'items': items,
            'shipping_fee': shipping_fee,
            'delivery_method': delivery_method,
            'delivery_county': delivery_county,
            'delivery_town': delivery_town,
            'mpesa_phone': mpesa_phone,
            'coupon_code': '',
            'cart_subtotal': cart.total_price,
            'discount_amount': Decimal('0.00'),
            'order_total_preview': cart.total_price + shipping_fee,
        },
    )


@login_required
def delivery_confirm(request):
    if request.user.role != 'customer':
        messages.error(request, 'Only customers can access delivery details.')
        return redirect('home')
    cart = _get_user_cart(request.user)
    items = cart.items.select_related('product')
    if not items.exists():
        messages.info(request, 'Your cart is empty.')
        return redirect('view_cart')

    delivery_county = request.session.get('delivery_county', '')
    delivery_town = request.session.get('delivery_town', '')
    delivery_method = request.session.get('delivery_method', Order.DELIVERY_PICKUP)

    if request.method == 'POST':
        delivery_county = request.POST.get('delivery_county', '').strip()
        delivery_town = request.POST.get('delivery_town', '').strip()
        delivery_method = request.POST.get('delivery_method', Order.DELIVERY_PICKUP)
        if delivery_method not in [Order.DELIVERY_PICKUP, Order.DELIVERY_DOOR]:
            delivery_method = Order.DELIVERY_PICKUP
        if not delivery_county:
            messages.error(request, 'Please select your delivery county.')
        else:
            request.session['delivery_county'] = delivery_county
            request.session['delivery_town'] = delivery_town
            request.session['delivery_method'] = delivery_method
            return redirect('checkout')

    shipping_fee = Decimal('0.00')
    if delivery_county:
        shipping_fee = _compute_shipping_fee(delivery_county, delivery_method)

    return render(
        request,
        'orders/delivery_confirm.html',
        {
            'cart': cart,
            'items': items,
            'delivery_county': delivery_county,
            'delivery_town': delivery_town,
            'delivery_method': delivery_method,
            'shipping_fee': shipping_fee,
            'cart_subtotal': cart.total_price,
            'order_total_preview': cart.total_price + shipping_fee,
        },
    )


@login_required
def order_success(request, order_id: int):
    # Confirmation page after checkout.
    if request.user.role != 'customer':
        messages.error(request, 'Only customers can access orders.')
        return redirect('home')
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    invoice = Invoice.objects.filter(order=order).first()
    receipt = Receipt.objects.filter(order=order).first()
    return render(request, 'orders/order_success.html', {'order': order, 'invoice': invoice, 'receipt': receipt})


@login_required
def order_receipt(request, order_id: int):
    # Printable receipt for a completed order.
    if request.user.role != 'customer':
        messages.error(request, 'Only customers can access orders.')
        return redirect('home')
    order = get_object_or_404(Order.objects.select_related('user'), pk=order_id, user=request.user)
    receipt = Receipt.objects.filter(order=order).first()
    items = order.items.select_related('product')
    return render(
        request,
        'receipt.html',
        {
            'order': order,
            'items': items,
            'receipt': receipt,
        },
    )


@login_required
def order_invoice(request, order_id: int):
    # Printable invoice for an order.
    if request.user.role != 'customer':
        messages.error(request, 'Only customers can access orders.')
        return redirect('home')
    order = get_object_or_404(Order.objects.select_related('user'), pk=order_id, user=request.user)
    invoice = Invoice.objects.filter(order=order).first()
    items = order.items.select_related('product')
    return render(
        request,
        'invoice.html',
        {
            'order': order,
            'items': items,
            'invoice': invoice,
        },
    )


@login_required
def order_detail(request, order_id: int):
    if request.user.role != 'customer':
        messages.error(request, 'Only customers can access orders.')
        return redirect('home')
    order = get_object_or_404(
        Order.objects.select_related('user').prefetch_related('items__product', 'tracking_entries'),
        pk=order_id,
        user=request.user,
    )
    latest_mpesa = (
        order.payments.filter(payment_method=Order.METHOD_MPESA)
        .order_by('-created_at')
        .first()
    )
    mpesa_phone = latest_mpesa.phone_number if latest_mpesa and latest_mpesa.phone_number else request.user.phone
    return render(
        request,
        'orders/order_detail.html',
        {
            'order': order,
            'latest_mpesa': latest_mpesa,
            'mpesa_phone': mpesa_phone,
        },
    )


@login_required
def user_orders(request):
    # Order history for the current user.
    if request.user.role != 'customer':
        messages.error(request, 'Only customers can access orders.')
        return redirect('home')
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'orders/user_orders.html', {'orders': orders})

# Create your views here.


@login_required
@require_POST
def retry_mpesa(request, order_id: int):
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    if order.payment_method != Order.METHOD_MPESA:
        messages.error(request, 'This order was not placed with M-Pesa.')
        return redirect('order_detail', order_id=order.id)
    if order.payment_status == Order.PAYMENT_PAID:
        messages.info(request, 'This order is already paid.')
        return redirect('order_detail', order_id=order.id)
    if not is_mpesa_configured():
        messages.error(request, 'M-Pesa is not configured yet. Please contact support.')
        return redirect('order_detail', order_id=order.id)

    raw_phone = request.POST.get('mpesa_phone', '').strip() or request.user.phone
    mpesa_phone = normalize_phone_number(raw_phone)
    if not mpesa_phone:
        messages.error(request, 'Enter a valid M-Pesa phone number (e.g. 07XXXXXXXX).')
        return redirect('order_detail', order_id=order.id)

    try:
        with transaction.atomic():
            account_reference = f'{settings.MPESA_ACCOUNT_REFERENCE} #{order.id}'
            transaction_desc = settings.MPESA_TRANSACTION_DESC
            response = stk_push(mpesa_phone, order.total_price, account_reference, transaction_desc)
            response_code = str(response.get('ResponseCode', ''))
            if response_code != '0':
                raise MpesaError(response.get('ResponseDescription', 'M-Pesa STK push failed.'))
            checkout_request_id = response.get('CheckoutRequestID', '')
            merchant_request_id = response.get('MerchantRequestID', '')
            Payment.objects.create(
                order=order,
                payment_method=Order.METHOD_MPESA,
                status=Payment.STATUS_PENDING,
                transaction_id=checkout_request_id or '',
                checkout_request_id=checkout_request_id or '',
                merchant_request_id=merchant_request_id or '',
                phone_number=mpesa_phone,
                amount=order.total_price,
            )
            order.payment_status = Order.PAYMENT_PENDING
            order.save(update_fields=['payment_status'])
    except MpesaError as exc:
        messages.error(request, str(exc))
        return redirect('order_detail', order_id=order.id)

    messages.success(request, 'STK prompt sent. Complete the payment on your phone.')
    return redirect('order_detail', order_id=order.id)
