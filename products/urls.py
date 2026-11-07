from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('products/', views.product_list, name='product_list'),
    path('products/<int:product_id>/', views.product_detail, name='product_detail'),
    path('category/<int:category_id>/', views.category_products, name='category_products'),
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/add/<int:product_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:product_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('seller/<int:seller_id>/', views.seller_detail, name='seller_detail'),
    path('seller/products/', views.seller_products, name='seller_products'),
    path('seller/products/new/', views.seller_product_create, name='seller_product_create'),
    path('seller/products/<int:product_id>/edit/', views.seller_product_edit, name='seller_product_edit'),
    path('sell/', views.sell_on_onlinestore, name='sell_on_onlinestore'),
    path('help/', views.help_center, name='help_center'),
    path('help/place-order/', views.help_place_order, name='help_place_order'),
    path('help/payment-options/', views.help_payment_options, name='help_payment_options'),
    path('help/returns-refunds/', views.help_returns_refunds, name='help_returns_refunds'),
    path('help/warranty/', views.help_warranty, name='help_warranty'),
    path('search/suggestions/', views.search_suggestions, name='search_suggestions'),
]
