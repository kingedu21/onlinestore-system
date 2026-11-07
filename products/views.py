from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Case, Count, Q, When
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from orders.models import OrderItem

from .forms import ProductSubmissionForm, ReviewForm, VariationFormSet
from .models import Category, HelpMessage, Product, ProductImage, Review, Seller, SubCategory, Wishlist


def _hero_products(qs, limit=3):
    return (
        qs.filter(is_approved=True)
        .exclude(image__isnull=True)
        .exclude(image='')
        .order_by('-created_at')[:limit]
    )


def home(request):
    # Landing page with featured products.
    categories = Category.objects.order_by('name')
    featured_products = (
        Product.objects.filter(is_approved=True)
        .annotate(avg_rating=Avg('reviews__rating'), review_count=Count('reviews'))
        .order_by('-created_at')[:8]
    )
    electronics_categories = Category.objects.filter(name__icontains='electronic')
    electronics_category = electronics_categories.first()
    electronics_products = _hero_products(
        Product.objects.filter(category__in=electronics_categories)
    )
    secondhand_products = _hero_products(
        Product.objects.filter(condition=Product.CONDITION_USED)
    )
    home_appliance_categories = Category.objects.filter(name__icontains='appliance')
    decor_categories = Category.objects.filter(name__icontains='decor')
    home_categories = Category.objects.filter(name__icontains='home')
    combined_home_categories = home_appliance_categories | decor_categories | home_categories
    if combined_home_categories.exists():
        home_appliance_categories = combined_home_categories
    elif not home_appliance_categories.exists():
        home_appliance_categories = home_categories
    home_appliance_category = home_appliance_categories.first()
    home_appliance_products = _hero_products(
        Product.objects.filter(category__in=home_appliance_categories)
    )
    category_sections = []
    for category in categories:
        products = (
            Product.objects.filter(category=category, is_approved=True)
            .annotate(avg_rating=Avg('reviews__rating'), review_count=Count('reviews'))
            .order_by('-created_at')[:8]
        )
        if products:
            category_sections.append({'category': category, 'products': products})
    best_seller_ids = list(
        OrderItem.objects.values('product_id')
        .annotate(order_count=Count('id'))
        .order_by('-order_count')
        .values_list('product_id', flat=True)[:8]
    )
    if best_seller_ids:
        preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(best_seller_ids)])
        best_sellers = (
            Product.objects.filter(id__in=best_seller_ids, is_approved=True)
            .annotate(avg_rating=Avg('reviews__rating'), review_count=Count('reviews'))
            .order_by(preserved)
        )
    else:
        best_sellers = Product.objects.none()
    context = {
        'categories': categories,
        'featured_products': featured_products,
        'best_sellers': best_sellers,
        'category_sections': category_sections,
        'hero_electronics': electronics_products,
        'hero_secondhand': secondhand_products,
        'hero_home_appliances': home_appliance_products,
        'electronics_category': electronics_category,
        'home_appliance_category': home_appliance_category,
    }
    return render(request, 'home.html', context)


def product_list(request):
    # Public catalog listing.
    products = (
        Product.objects.select_related('category')
        .filter(is_approved=True)
        .annotate(avg_rating=Avg('reviews__rating'), review_count=Count('reviews'))
        .order_by('-created_at')
    )
    category_id = request.GET.get('category')
    if category_id:
        products = products.filter(category_id=category_id)
    subcategory_id = request.GET.get('subcategory')
    if subcategory_id:
        products = products.filter(subcategory_id=subcategory_id)
    query = request.GET.get('q', '').strip()
    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(category__name__icontains=query)
        )
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    in_stock = request.GET.get('in_stock')
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)
    if in_stock:
        products = products.filter(stock__gt=0)
    condition = request.GET.get('condition')
    allowed_conditions = {Product.CONDITION_NEW, Product.CONDITION_USED, Product.CONDITION_REFURBISHED}
    if condition in allowed_conditions:
        products = products.filter(condition=condition)
    categories = Category.objects.order_by('name')
    subcategories = SubCategory.objects.order_by('name')
    return render(
        request,
        'products/product_list.html',
        {
            'products': products,
            'categories': categories,
            'subcategories': subcategories,
            'active_category': category_id,
            'active_subcategory': subcategory_id,
            'query': query,
            'min_price': min_price,
            'max_price': max_price,
            'in_stock': in_stock,
            'condition': condition,
        },
    )


def search_suggestions(request):
    q = (request.GET.get('q') or '').strip()
    if not q:
        return JsonResponse({'suggestions': []})
    product_names = (
        Product.objects.filter(is_approved=True, name__icontains=q)
        .values_list('name', flat=True)
        .distinct()[:5]
    )
    category_names = (
        Category.objects.filter(name__icontains=q)
        .values_list('name', flat=True)
        .distinct()[:5]
    )
    suggestions = list(product_names) + [f'Category: {name}' for name in category_names]
    return JsonResponse({'suggestions': suggestions[:8]})


def category_products(request, category_id: int):
    category = get_object_or_404(Category, pk=category_id)
    products = (
        Product.objects.filter(category=category, is_approved=True)
        .select_related('category')
        .annotate(avg_rating=Avg('reviews__rating'), review_count=Count('reviews'))
        .order_by('-created_at')
    )
    subcategories = SubCategory.objects.filter(category=category).order_by('name')
    subcategory_id = request.GET.get('subcategory')
    if subcategory_id:
        products = products.filter(subcategory_id=subcategory_id)
    return render(
        request,
        'products/category_products.html',
        {
            'category': category,
            'products': products,
            'subcategories': subcategories,
            'active_subcategory': subcategory_id,
        },
    )


def product_detail(request, product_id: int):
    # Single product details page.
    product_qs = Product.objects.select_related('category')
    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser or request.user.role == 'admin'):
        product = get_object_or_404(product_qs, pk=product_id)
    elif request.user.is_authenticated and request.user.role == 'seller':
        seller = Seller.objects.filter(user=request.user).first()
        if seller:
            product = get_object_or_404(
                product_qs,
                Q(pk=product_id, is_approved=True) | Q(pk=product_id, seller=seller),
            )
        else:
            product = get_object_or_404(product_qs, pk=product_id, is_approved=True)
    else:
        product = get_object_or_404(product_qs, pk=product_id, is_approved=True)
    related_products = (
        Product.objects.filter(category=product.category)
        .exclude(id=product.id)
        .annotate(avg_rating=Avg('reviews__rating'), review_count=Count('reviews'))
        .order_by('-created_at')[:4]
    )
    reviews = product.reviews.select_related('user').order_by('-created_at')
    average_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
    review_form = ReviewForm()
    active_variations = product.variations.filter(is_active=True)
    initial_variation_id = active_variations.first().id if active_variations.exists() else None

    if request.method == 'POST' and request.user.is_authenticated and request.user.role == 'customer':
        review_form = ReviewForm(request.POST)
        if review_form.is_valid():
            Review.objects.update_or_create(
                product=product,
                user=request.user,
                defaults={
                    'rating': int(review_form.cleaned_data['rating']),
                    'comment': review_form.cleaned_data['comment'],
                },
            )
            return redirect('product_detail', product_id=product.id)

    is_in_wishlist = False
    if request.user.is_authenticated:
        is_in_wishlist = Wishlist.objects.filter(user=request.user, product=product).exists()

    return render(
        request,
        'products/product_detail.html',
        {
            'product': product,
            'related_products': related_products,
            'reviews': reviews,
            'average_rating': round(average_rating, 1),
            'review_form': review_form,
            'is_in_wishlist': is_in_wishlist,
            'active_variations': active_variations,
            'initial_variation_id': initial_variation_id,
        },
    )


@login_required
def add_to_wishlist(request, product_id: int):
    product = get_object_or_404(Product, pk=product_id)
    Wishlist.objects.get_or_create(user=request.user, product=product)
    messages.success(request, f'{product.name} added to your wishlist.')
    return redirect('product_detail', product_id=product.id)


@login_required
def remove_from_wishlist(request, product_id: int):
    product = get_object_or_404(Product, pk=product_id)
    Wishlist.objects.filter(user=request.user, product=product).delete()
    messages.success(request, f'{product.name} removed from your wishlist.')
    return redirect('product_detail', product_id=product.id)


@login_required
def wishlist_view(request):
    items = Wishlist.objects.filter(user=request.user).select_related('product')
    return render(request, 'products/wishlist.html', {'items': items})


def seller_detail(request, seller_id: int):
    seller = get_object_or_404(Seller, pk=seller_id)
    products = (
        Product.objects.filter(seller=seller, is_approved=True)
        .annotate(avg_rating=Avg('reviews__rating'), review_count=Count('reviews'))
        .order_by('-created_at')
    )
    return render(
        request,
        'products/seller_detail.html',
        {'seller': seller, 'products': products},
    )


def sell_on_onlinestore(request):
    return render(request, 'sell_on_onlinestore.html')


def help_center(request):
    name_value = ''
    email_value = ''
    if request.user.is_authenticated:
        name_value = request.user.get_full_name() or request.user.get_username()
        email_value = request.user.email or ''

    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()
        email = (request.POST.get('email') or '').strip()
        message = (request.POST.get('message') or '').strip()
        if not name or not email or not message:
            messages.error(request, 'Please fill in all fields before submitting.')
        else:
            HelpMessage.objects.create(
                user=request.user if request.user.is_authenticated else None,
                name=name,
                email=email,
                message=message,
            )
            messages.success(request, 'Thanks for reaching out. We have received your message.')
            return redirect('help_center')

        name_value = name or name_value
        email_value = email or email_value

    return render(
        request,
        'help/help_center.html',
        {'support_name': name_value, 'support_email': email_value},
    )


def help_place_order(request):
    return render(request, 'help/place_order.html')


def help_payment_options(request):
    return render(request, 'help/payment_options.html')


def help_returns_refunds(request):
    return render(request, 'help/returns_refunds.html')


def help_warranty(request):
    return render(request, 'help/warranty.html')


@login_required
def seller_products(request):
    if request.user.role != 'seller':
        messages.error(request, 'Only approved sellers can access this page.')
        return redirect('home')
    seller = Seller.objects.filter(user=request.user, is_active=True).first()
    if not seller:
        messages.error(request, 'Only approved sellers can access this page.')
        return redirect('home')
    products = Product.objects.filter(seller=seller).order_by('-created_at')
    return render(request, 'products/seller_products.html', {'seller': seller, 'products': products})


@login_required
def seller_product_create(request):
    is_admin = request.user.role == 'admin' or request.user.is_staff or request.user.is_superuser
    if request.user.role != 'seller' and not is_admin:
        messages.error(request, 'Only approved sellers can list products.')
        return redirect('home')
    seller = Seller.objects.filter(user=request.user, is_active=True).first() if not is_admin else None
    if not seller and not is_admin:
        messages.error(request, 'Only approved sellers can list products.')
        return redirect('home')

    if request.method == 'POST':
        form = ProductSubmissionForm(request.POST, request.FILES, show_seller=is_admin)
        formset = VariationFormSet(request.POST, prefix='variations')
        if form.is_valid() and formset.is_valid():
            product = form.save(commit=False)
            if is_admin:
                selected_seller = form.cleaned_data.get('seller')
                if not selected_seller:
                    form.add_error('seller', 'Select a seller for this product.')
                    return render(
                        request,
                        'products/seller_product_form.html',
                        {'form': form, 'formset': formset, 'seller': seller},
                    )
                product.seller = selected_seller
            else:
                product.seller = seller
                product.is_approved = False
            product.save()
            extra_images = form.cleaned_data.get('extra_images', [])
            for image in extra_images:
                ProductImage.objects.create(product=product, image=image)
            for variation_form in formset:
                if variation_form.cleaned_data and not variation_form.cleaned_data.get('DELETE'):
                    variation = variation_form.save(commit=False)
                    if not variation.name or not variation.value:
                        continue
                    variation.product = product
                    variation.save()
            messages.success(request, 'Product submitted for approval.')
            return redirect('seller_products')
        else:
            if form.errors:
                messages.error(request, f'Please fix the product form errors: {form.errors.as_text()}')
            if any(f.errors for f in formset):
                messages.error(request, 'Please fix the variation errors.')
    else:
        form = ProductSubmissionForm(show_seller=is_admin)
        formset = VariationFormSet(prefix='variations')
    return render(
        request,
        'products/seller_product_form.html',
        {'form': form, 'formset': formset, 'seller': seller},
    )


@login_required
def seller_product_edit(request, product_id: int):
    is_admin = request.user.role == 'admin' or request.user.is_staff or request.user.is_superuser
    if request.user.role != 'seller' and not is_admin:
        messages.error(request, 'Only approved sellers can edit products.')
        return redirect('home')
    seller = Seller.objects.filter(user=request.user, is_active=True).first() if not is_admin else None
    if not seller and not is_admin:
        messages.error(request, 'Only approved sellers can edit products.')
        return redirect('home')
    product = get_object_or_404(Product, pk=product_id, seller=seller) if not is_admin else get_object_or_404(Product, pk=product_id)

    if request.method == 'POST':
        form = ProductSubmissionForm(request.POST, request.FILES, instance=product, show_seller=is_admin)
        formset = VariationFormSet(request.POST, prefix='variations')
        if form.is_valid() and formset.is_valid():
            product = form.save(commit=False)
            if is_admin:
                selected_seller = form.cleaned_data.get('seller')
                if selected_seller:
                    product.seller = selected_seller
            else:
                product.seller = seller
                product.is_approved = False
            product.save()
            extra_images = form.cleaned_data.get('extra_images', [])
            for image in extra_images:
                ProductImage.objects.create(product=product, image=image)
            for variation_form in formset:
                if variation_form.cleaned_data and not variation_form.cleaned_data.get('DELETE'):
                    variation = variation_form.save(commit=False)
                    if not variation.name or not variation.value:
                        continue
                    variation.product = product
                    variation.save()
            messages.success(request, 'Product updated and submitted for approval.')
            return redirect('seller_products')
        else:
            if form.errors:
                messages.error(request, f'Please fix the product form errors: {form.errors.as_text()}')
            if any(f.errors for f in formset):
                messages.error(request, 'Please fix the variation errors.')
    else:
        form = ProductSubmissionForm(instance=product, show_seller=is_admin)
        formset = VariationFormSet(prefix='variations')
    return render(
        request,
        'products/seller_product_form.html',
        {'form': form, 'formset': formset, 'seller': seller},
    )
