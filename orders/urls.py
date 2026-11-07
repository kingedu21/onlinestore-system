from django.urls import path

from . import views

urlpatterns = [
    path('delivery/', views.delivery_confirm, name='delivery_confirm'),
    path('checkout/', views.checkout, name='checkout'),
    path('success/<int:order_id>/', views.order_success, name='order_success'),
    path('invoice/<int:order_id>/', views.order_invoice, name='order_invoice'),
    path('receipt/<int:order_id>/', views.order_receipt, name='order_receipt'),
    path('detail/<int:order_id>/', views.order_detail, name='order_detail'),
    path('retry-mpesa/<int:order_id>/', views.retry_mpesa, name='retry_mpesa'),
    path('my/', views.user_orders, name='user_orders'),
]
