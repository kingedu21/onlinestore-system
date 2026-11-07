from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.core.mail import send_mail
from django.utils.html import format_html
from django.utils.text import slugify

from .models import Category, HelpMessage, Product, ProductImage, Review, Seller, SellerApplication, SubCategory, Variation, Wishlist


class SellerAdminForm(forms.ModelForm):
    user_username = forms.CharField(required=False, help_text='Optional. If blank, username is based on email.')
    user_password = forms.CharField(required=False, help_text='Optional. If blank, a temporary password is generated.')

    class Meta:
        model = Seller
        fields = '__all__'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category')
    list_filter = ('category',)
    search_fields = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('image_preview', 'name', 'price', 'stock', 'category', 'subcategory', 'seller', 'condition', 'is_approved', 'created_at')
    list_filter = ('category', 'subcategory', 'condition', 'seller', 'is_approved')
    search_fields = ('name', 'description')
    inlines = []
    actions = ['approve_products', 'mark_pending']

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 6px;" />',
                obj.image.url,
            )
        return '-'

    image_preview.short_description = 'Image'

    def approve_products(self, request, queryset):
        updated = queryset.update(is_approved=True)
        messages.success(request, f'Approved {updated} product(s).')

    def mark_pending(self, request, queryset):
        updated = queryset.update(is_approved=False)
        messages.success(request, f'Marked {updated} product(s) as pending.')

    approve_products.short_description = 'Approve selected products'
    mark_pending.short_description = 'Mark selected products as pending'


class VariationInline(admin.TabularInline):
    model = Variation
    extra = 1


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


ProductAdmin.inlines = [VariationInline, ProductImageInline]


@admin.register(Seller)
class SellerAdmin(admin.ModelAdmin):
    form = SellerAdminForm
    list_display = ('store_name', 'user', 'email', 'rating', 'phone', 'is_active', 'is_suspicious', 'created_at')
    list_filter = ('is_active', 'is_suspicious')
    search_fields = ('store_name', 'email', 'phone', 'user__username')
    fieldsets = (
        (None, {'fields': ('store_name', 'name', 'email', 'phone', 'user', 'is_active')}),
        ('Account Credentials', {'fields': ('user_username', 'user_password')}),
        ('Status', {'fields': ('rating', 'is_suspicious', 'suspicious_reason')}),
    )


@admin.register(SellerApplication)
class SellerApplicationAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'business_name', 'email', 'phone_number', 'mpesa_number', 'id_number', 'business_registration', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('full_name', 'business_name', 'email', 'phone_number', 'mpesa_number', 'id_number', 'business_registration')

    def save_model(self, request, obj, form, change):
        user_should_be_active = obj.status == SellerApplication.STATUS_APPROVED
        if not obj.user and obj.email:
            from accounts.models import User

            email = obj.email.lower()
            username = (form.cleaned_data.get('user_username') or '').strip() or email
            counter = 1
            while User.objects.filter(username=username).exists():
                counter += 1
                if '@' in email:
                    username = f'{email.split("@")[0]}{counter}@{email.split("@")[1]}'
                else:
                    username = f'{email}{counter}'
            raw_password = (form.cleaned_data.get('user_password') or '').strip()
            temp_password = raw_password or User.objects.make_random_password(length=10)
            user = User.objects.create_user(username=username, email=email, password=temp_password)
            user.role = 'seller'
            user.is_active = user_should_be_active
            user.must_change_password = True
            user.save(update_fields=['role', 'is_active', 'must_change_password'])
            obj.user = user
            subject = 'Your Seller Account Credentials'
            body = (
                'Hello,\n\n'
                'Your seller account has been created.\n'
                f'Username: {username}\n'
                f'Password: {temp_password}\n\n'
                'Please log in and change your password after first sign in.'
            )
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None)
            if email:
                send_mail(subject, body, from_email, [email], fail_silently=True)
            messages.success(
                request,
                f'Seller account created for {email}. Username: {username}. Password: {temp_password}',
            )
        if obj.user:
            obj.user.role = 'seller'
            obj.user.is_staff = False
            obj.user.is_active = user_should_be_active
            obj.user.save(update_fields=['role', 'is_staff', 'is_active'])

            seller_defaults = {
                'store_name': obj.business_name,
                'name': obj.full_name,
                'email': obj.email,
                'phone': obj.phone_number,
                'is_active': user_should_be_active,
            }
            seller, _created = Seller.objects.get_or_create(user=obj.user, defaults=seller_defaults)
            if not _created:
                seller.store_name = obj.business_name
                seller.name = obj.full_name
                seller.email = obj.email
                seller.phone = obj.phone_number
                seller.is_active = user_should_be_active
                seller.save(update_fields=['store_name', 'name', 'email', 'phone', 'is_active'])
        super().save_model(request, obj, form, change)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'created_at')
    list_filter = ('rating',)
    search_fields = ('product__name', 'user__username', 'comment')


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'created_at')
    search_fields = ('user__username', 'product__name')


@admin.register(HelpMessage)
class HelpMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'is_resolved', 'created_at')
    list_filter = ('is_resolved', 'created_at')
    search_fields = ('name', 'email', 'message')
