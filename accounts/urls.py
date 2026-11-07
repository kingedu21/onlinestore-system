from django.urls import include, path

from . import views

urlpatterns = [
    path('login/', views.LoginViewWithMessage.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register, name='register'),
    path('me/', views.account_detail, name='account_detail'),
    path('become-seller/', views.become_seller, name='become_seller'),
    path('password_change/', views.force_password_change, name='password_change'),
    path('', include('django.contrib.auth.urls')),
]
