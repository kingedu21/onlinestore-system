from collections import deque
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test

from django.db.models import Avg, Count, DecimalField, F, Q, Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import User
from orders.models import Commission, Order, OrderItem
from payments.models import Payment
from products.models import Product, Review, Seller, SellerApplication
from accounts.models import Notification
from products.models import Review


def _is_admin(user):
    return user.is_superuser or user.is_staff or user.role == User.ROLE_ADMIN


def _is_seller(user):
    return user.role == User.ROLE_SELLER


@login_required
@user_passes_test(_is_admin)
def analytics(request):
    # Admin dashboard metrics and insights.
    total_customers = User.objects.filter(role=User.ROLE_CUSTOMER).count()
    total_orders = Order.objects.count()
    product_sales = (
        Order.objects.aggregate(
            total=Sum(F('total_price') - F('shipping_fee'), output_field=DecimalField())
        )['total'] or 0
    )
    shipping_revenue = Order.objects.aggregate(total=Sum('shipping_fee'))['total'] or 0
    total_revenue = product_sales + shipping_revenue
    total_products = Product.objects.count()
    total_sellers = Seller.objects.count()
    total_commission = Commission.objects.aggregate(total=Sum('commission_amount'))['total'] or 0
    total_seller_payouts = (
        Commission.objects.filter(seller_payout_status=Commission.PAYOUT_PAID)
        .aggregate(total=Sum('seller_earning'))
        .get('total') or 0
    )
    pending_orders = Order.objects.filter(
        status__in=[
            Order.STATUS_PENDING,
            Order.STATUS_PROCESSING,
            Order.STATUS_SHIPPED,
            Order.STATUS_OUT_FOR_DELIVERY,
        ]
    ).count()
    completed_orders = Order.objects.filter(status=Order.STATUS_COMPLETED).count()

    recent_orders = Order.objects.select_related('user').order_by('-created_at')[:5]
    low_stock = Product.objects.filter(stock__lt=5).order_by('stock')[:10]

    top_products = (
        OrderItem.objects.values('product__name')
        .annotate(
            total_orders=Count('id'),
            total_sales=Sum(F('price') * F('quantity'), output_field=DecimalField()),
        )
        .order_by('-total_orders')[:5]
    )

    top_sellers = (
        Commission.objects.values('seller__name')
        .annotate(
            total_sales=Sum(F('seller_earning') + F('commission_amount'), output_field=DecimalField()),
            total_commission=Sum('commission_amount'),
        )
        .order_by('-total_sales')[:5]
    )

    top_categories = (
        OrderItem.objects.values('product__category__name')
        .annotate(
            total_sales=Sum(F('price') * F('quantity'), output_field=DecimalField()),
        )
        .order_by('-total_sales')[:5]
    )

    now = timezone.now()
    first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start_date = (first_of_month - timedelta(days=365)).replace(day=1)
    monthly_sales = (
        Order.objects.filter(created_at__gte=start_date)
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(total_sales=Sum('total_price'), total_orders=Count('id'))
        .order_by('month')
    )

    monthly_commission = (
        Commission.objects.filter(created_at__gte=start_date)
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(total_commission=Sum('commission_amount'))
        .order_by('month')
    )

    sales_map = {
        item['month'].strftime('%Y-%m'): {
            'sales': float(item['total_sales'] or 0),
            'orders': item['total_orders'],
        }
        for item in monthly_sales
    }
    commission_map = {
        item['month'].strftime('%Y-%m'): float(item['total_commission'] or 0)
        for item in monthly_commission
    }

    chart_labels = []
    chart_sales = []
    chart_orders = []
    chart_commission = []
    year = first_of_month.year
    month = first_of_month.month
    months = []
    for offset in range(11, -1, -1):
        m = month - offset
        y = year
        while m <= 0:
            m += 12
            y -= 1
        months.append(first_of_month.replace(year=y, month=m))

    for month_dt in months:
        key = month_dt.strftime('%Y-%m')
        chart_labels.append(month_dt.strftime('%b %Y'))
        chart_sales.append(sales_map.get(key, {}).get('sales', 0))
        chart_orders.append(sales_map.get(key, {}).get('orders', 0))
        chart_commission.append(commission_map.get(key, 0))

    context = {
        'total_customers': total_customers,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'product_sales': product_sales,
        'shipping_revenue': shipping_revenue,
        'total_products': total_products,
        'total_sellers': total_sellers,
        'total_commission': total_commission,
        'total_seller_payouts': total_seller_payouts,
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
        'recent_orders': recent_orders,
        'top_products': top_products,
        'top_sellers': top_sellers,
        'top_categories': top_categories,
        'low_stock': low_stock,
        'chart_labels': chart_labels,
        'chart_sales': chart_sales,
        'chart_orders': chart_orders,
        'chart_commission': chart_commission,
    }
    return render(request, 'dashboard/dashboard.html', context)


@login_required
@user_passes_test(_is_admin)
def commission_report(request):
    commissions = Commission.objects.select_related('order', 'product', 'seller').order_by('-created_at')[:200]
    return render(request, 'dashboard/commission_report.html', {'commissions': commissions})


@login_required
def seller_dashboard(request):
    if not _is_seller(request.user):
        return redirect('home')
    seller = Seller.objects.filter(user=request.user, is_active=True).first()
    return _render_seller_dashboard(request, seller)

def _render_seller_dashboard(request, seller):
    if not seller:
        return render(request, 'dashboard/seller_dashboard.html', {'seller': None})

    total_sales = (
        Commission.objects.filter(seller=seller)
        .aggregate(total=Sum(F('seller_earning') + F('commission_amount'), output_field=DecimalField()))
        .get('total') or 0
    )
    total_commission = Commission.objects.filter(seller=seller).aggregate(total=Sum('commission_amount')).get('total') or 0
    total_earnings = Commission.objects.filter(seller=seller).aggregate(total=Sum('seller_earning')).get('total') or 0
    orders_received = Order.objects.filter(items__product__seller=seller).distinct().count()
    orders_pending_shipment = Order.objects.filter(
        items__product__seller=seller,
        status__in=[
            Order.STATUS_PENDING,
            Order.STATUS_PROCESSING,
            Order.STATUS_SHIPPED,
            Order.STATUS_OUT_FOR_DELIVERY,
        ],
    ).distinct().count()
    completed_orders = Order.objects.filter(
        items__product__seller=seller, status=Order.STATUS_COMPLETED
    ).distinct().count()

    now = timezone.now()
    first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start_date = (first_of_month - timedelta(days=365)).replace(day=1)
    monthly_sales = (
        Commission.objects.filter(seller=seller, created_at__gte=start_date)
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(total_sales=Sum(F('seller_earning') + F('commission_amount'), output_field=DecimalField()),
                  total_orders=Count('id'),
                  total_earnings=Sum('seller_earning'))
        .order_by('month')
    )
    sales_map = {
        item['month'].strftime('%Y-%m'): {
            'sales': float(item['total_sales'] or 0),
            'orders': item['total_orders'],
            'earnings': float(item['total_earnings'] or 0),
        }
        for item in monthly_sales
    }
    chart_labels = []
    chart_sales = []
    chart_orders = []
    chart_earnings = []
    year = first_of_month.year
    month = first_of_month.month
    months = []
    for offset in range(11, -1, -1):
        m = month - offset
        y = year
        while m <= 0:
            m += 12
            y -= 1
        months.append(first_of_month.replace(year=y, month=m))
    for month_dt in months:
        key = month_dt.strftime('%Y-%m')
        chart_labels.append(month_dt.strftime('%b %Y'))
        chart_sales.append(sales_map.get(key, {}).get('sales', 0))
        chart_orders.append(sales_map.get(key, {}).get('orders', 0))
        chart_earnings.append(sales_map.get(key, {}).get('earnings', 0))

    recent_orders = Order.objects.filter(items__product__seller=seller).distinct().order_by('-created_at')[:5]
    total_products = Product.objects.filter(seller=seller).count()
    review_count = Review.objects.filter(product__seller=seller).count()
    low_stock = Product.objects.filter(seller=seller, stock__lt=5).order_by('stock')[:5]

    context = {
        'seller': seller,
        'total_sales': total_sales,
        'total_commission': total_commission,
        'total_earnings': total_earnings,
        'orders_received': orders_received,
        'orders_pending_shipment': orders_pending_shipment,
        'completed_orders': completed_orders,
        'total_products': total_products,
        'recent_orders': recent_orders,
        'review_count': review_count,
        'low_stock': low_stock,
        'chart_labels': chart_labels,
        'chart_sales': chart_sales,
        'chart_orders': chart_orders,
        'chart_earnings': chart_earnings,
    }
    return render(request, 'dashboard/seller_dashboard.html', context)


@login_required
@user_passes_test(_is_admin)
def admin_dashboard(request):
    return analytics(request)


@login_required
@user_passes_test(_is_admin)
def admin_sellers(request):
    sellers = Seller.objects.all()
    rows = []
    for seller in sellers:
        total_sales = (
            Commission.objects.filter(seller=seller)
            .aggregate(total=Sum(F('seller_earning') + F('commission_amount'), output_field=DecimalField()))
            .get('total') or 0
        )
        total_commission = Commission.objects.filter(seller=seller).aggregate(total=Sum('commission_amount')).get('total') or 0
        total_earnings = Commission.objects.filter(seller=seller).aggregate(total=Sum('seller_earning')).get('total') or 0
        total_orders = Order.objects.filter(items__product__seller=seller).distinct().count()
        total_products = Product.objects.filter(seller=seller).count()
        rows.append(
            {
                'seller': seller,
                'total_sales': total_sales,
                'total_commission': total_commission,
                'total_earnings': total_earnings,
                'total_orders': total_orders,
                'total_products': total_products,
            }
        )
    return render(request, 'dashboard/admin_sellers.html', {'rows': rows})


@login_required
@user_passes_test(_is_admin)
def seller_performance(request):
    sellers = Seller.objects.all()
    rows = []
    for seller in sellers:
        products_listed = Product.objects.filter(seller=seller).count()
        order_items = OrderItem.objects.filter(product__seller=seller)
        total_sales = order_items.aggregate(total=Sum(F('price') * F('quantity'), output_field=DecimalField())).get('total') or 0
        total_orders = Order.objects.filter(items__product__seller=seller).distinct().count()
        avg_rating = Review.objects.filter(product__seller=seller).aggregate(avg=Avg('rating')).get('avg') or 0
        cancelled_orders = Order.objects.filter(items__product__seller=seller, status=Order.STATUS_CANCELLED).distinct().count()
        rows.append(
            {
                'seller': seller,
                'products_listed': products_listed,
                'total_sales': total_sales,
                'total_orders': total_orders,
                'avg_rating': round(avg_rating, 1) if avg_rating else 0,
                'cancelled_orders': cancelled_orders,
            }
        )
    rows.sort(key=lambda item: item['total_sales'], reverse=True)
    top_rows = rows[:10]
    chart_labels = [item['seller'].store_name or str(item['seller']) for item in top_rows]
    chart_sales = [float(item['total_sales']) for item in top_rows]
    chart_orders = [item['total_orders'] for item in top_rows]

    total_sellers = len(rows)
    total_sales = sum(item['total_sales'] for item in rows)
    total_orders = sum(item['total_orders'] for item in rows)
    avg_rating_overall = (
        sum(item['avg_rating'] for item in rows) / total_sellers if total_sellers else 0
    )

    return render(
        request,
        'dashboard/seller_performance.html',
        {
            'rows': rows,
            'chart_labels': chart_labels,
            'chart_sales': chart_sales,
            'chart_orders': chart_orders,
            'total_sellers': total_sellers,
            'total_sales': total_sales,
            'total_orders': total_orders,
            'avg_rating_overall': round(avg_rating_overall, 1) if avg_rating_overall else 0,
        },
    )


@login_required
@user_passes_test(_is_admin)
def seller_applications(request):
    applications = SellerApplication.objects.select_related('user').order_by('-created_at')
    return render(request, 'dashboard/seller_applications.html', {'applications': applications})


@login_required
@user_passes_test(_is_admin)
def approve_seller_application(request, application_id: int):
    application = get_object_or_404(SellerApplication, pk=application_id)
    if application.status != SellerApplication.STATUS_APPROVED:
        seller, _created = Seller.objects.get_or_create(
            user=application.user,
            defaults={
                'store_name': application.business_name,
                'name': application.full_name,
                'email': application.email,
                'phone': application.phone_number,
                'is_active': True,
            },
        )
        seller.is_active = True
        seller.save(update_fields=['is_active'])
        application.user.role = 'seller'
        application.user.save(update_fields=['role'])
        application.status = SellerApplication.STATUS_APPROVED
        application.save(update_fields=['status'])
        Notification.objects.create(
            user=application.user,
            message='Your seller application has been approved. You can now access the seller dashboard.',
        )
        messages.success(request, 'Seller application approved.')
    return redirect('seller_applications')


@login_required
@user_passes_test(_is_admin)
def reject_seller_application(request, application_id: int):
    application = get_object_or_404(SellerApplication, pk=application_id)
    application.status = SellerApplication.STATUS_REJECTED
    application.save(update_fields=['status'])
    Notification.objects.create(
        user=application.user,
        message='Your seller application was not approved.',
    )
    messages.warning(request, 'Seller application rejected.')
    return redirect('seller_applications')


@login_required
@user_passes_test(_is_admin)
def admin_seller_dashboard(request, seller_id: int):
    seller = get_object_or_404(Seller, pk=seller_id)
    return _render_seller_dashboard(request, seller)


@login_required
@user_passes_test(_is_admin)
def toggle_seller_status(request, seller_id: int):
    seller = get_object_or_404(Seller, pk=seller_id)
    seller.is_active = not seller.is_active
    seller.save(update_fields=['is_active'])
    if seller.user:
        seller.user.is_active = seller.is_active
        seller.user.save(update_fields=['is_active'])
    return redirect('admin_sellers')


@login_required
@user_passes_test(_is_admin)
def mpesa_webhook_logs(request):
    status = request.GET.get('status', '').strip()
    result_code = request.GET.get('result_code', '').strip()
    query = request.GET.get('q', '').strip()

    payments = Payment.objects.filter(payment_method=Order.METHOD_MPESA).select_related('order').order_by('-created_at')
    if status:
        payments = payments.filter(status=status)
    if result_code:
        payments = payments.filter(result_code=result_code)
    if query:
        payments = payments.filter(
            Q(order__id__icontains=query)
            | Q(mpesa_receipt_number__icontains=query)
            | Q(checkout_request_id__icontains=query)
            | Q(phone_number__icontains=query)
        )

    payments = payments[:200]
    return render(
        request,
        'dashboard/mpesa_webhook_logs.html',
        {
            'payments': payments,
            'status': status,
            'result_code': result_code,
            'query': query,
        },
    )


@login_required
@user_passes_test(_is_admin)
def mpesa_callback_file_logs(request):
    log_path = Path(settings.BASE_DIR) / 'mpesa_callbacks.log'
    lines = deque(maxlen=200)
    error = ''
    if log_path.exists():
        try:
            with log_path.open('r', encoding='utf-8', errors='ignore') as handle:
                for line in handle:
                    lines.append(line.rstrip('\n'))
        except OSError as exc:
            error = f'Could not read log file: {exc}'
    else:
        error = 'Log file not found yet. Trigger a callback to generate it.'

    return render(
        request,
        'dashboard/mpesa_callback_file_logs.html',
        {
            'log_path': str(log_path),
            'lines': list(lines),
            'error': error,
        },
    )
