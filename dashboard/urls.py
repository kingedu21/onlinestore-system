from django.urls import path

from . import views

urlpatterns = [
    path('', views.analytics, name='dashboard'),
    path('commission-report/', views.commission_report, name='commission_report'),
    path('seller/', views.seller_dashboard, name='seller_dashboard'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/sellers/', views.admin_sellers, name='admin_sellers'),
    path('admin/sellers/<int:seller_id>/', views.admin_seller_dashboard, name='admin_seller_dashboard'),
    path('admin/sellers/<int:seller_id>/toggle/', views.toggle_seller_status, name='toggle_seller_status'),
    path('admin/mpesa-webhooks/', views.mpesa_webhook_logs, name='mpesa_webhook_logs'),
    path('admin/mpesa-callback-file/', views.mpesa_callback_file_logs, name='mpesa_callback_file_logs'),
    path('admin/seller-applications/', views.seller_applications, name='seller_applications'),
    path('admin/seller-applications/<int:application_id>/approve/', views.approve_seller_application, name='approve_seller_application'),
    path('admin/seller-applications/<int:application_id>/reject/', views.reject_seller_application, name='reject_seller_application'),
    path('admin/seller-performance/', views.seller_performance, name='seller_performance'),
]
