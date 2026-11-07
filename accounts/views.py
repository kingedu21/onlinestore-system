from django.contrib import messages
from django.contrib.auth import login, logout as auth_logout
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST

from .forms import AccountUpdateForm, CustomUserCreationForm, SellerApplicationForm
from .models import Notification
from products.models import Seller, SellerApplication


def register(request):
    # Simple user registration.
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='accounts.auth_backend.EmailOrUsernameBackend')
            return redirect('home')
    else:
        form = CustomUserCreationForm()

    return render(request, 'registration/register.html', {'form': form})


class LoginViewWithMessage(LoginView):
    def form_valid(self, form):
        messages.success(self.request, 'Login successful. Welcome back!')
        return super().form_valid(form)

    def get_success_url(self):
        redirect_to = self.get_redirect_url()
        if redirect_to:
            return redirect_to
        user = self.request.user
        if user.role == 'seller' and Seller.objects.filter(user=user, is_active=True).exists():
            return reverse_lazy('seller_dashboard')
        return reverse_lazy('home')


@require_POST
def logout_view(request):
    auth_logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')


@login_required
def account_detail(request):
    # Basic account summary.
    if request.method == 'POST':
        form = AccountUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('account_detail')
    else:
        form = AccountUpdateForm(instance=request.user)

    notifications = Notification.objects.filter(user=request.user)[:20]
    return render(request, 'accounts/account_detail.html', {'form': form, 'notifications': notifications})


@login_required
def become_seller(request):
    if request.user.role in ['admin', 'seller']:
        messages.error(request, 'Admins and sellers cannot apply.')
        return redirect('home')
    if Seller.objects.filter(user=request.user).exists():
        messages.error(request, 'You already have a seller account.')
        return redirect('home')
    existing_app = SellerApplication.objects.filter(user=request.user).order_by('-created_at').first()
    if existing_app and existing_app.status in [SellerApplication.STATUS_PENDING, SellerApplication.STATUS_APPROVED]:
        messages.info(request, 'You already have a seller application in progress.')
        return redirect('home')
    if existing_app and existing_app.status == SellerApplication.STATUS_REJECTED and request.method == 'GET':
        messages.warning(request, 'Your seller application was not approved.')

    if request.method == 'POST':
        form = SellerApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.user = request.user
            application.status = SellerApplication.STATUS_PENDING
            application.save()
            messages.success(request, 'Your seller application has been submitted and is waiting for admin approval.')
            return redirect('home')
    else:
        form = SellerApplicationForm(initial={'email': request.user.email})
    return render(request, 'accounts/become_seller.html', {'form': form, 'existing_app': existing_app})


class ForcePasswordChangeView(PasswordChangeView):
    success_url = reverse_lazy('password_change_done')

    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.request.user
        if getattr(user, 'must_change_password', False):
            user.must_change_password = False
            user.save(update_fields=['must_change_password'])
        return response


force_password_change = ForcePasswordChangeView.as_view()
