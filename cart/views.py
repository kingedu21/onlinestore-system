from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from products.models import Product, Variation

from .models import Cart


def _get_user_cart(user):
    # Ensure each user has a cart.
    cart, _created = Cart.objects.get_or_create(user=user)
    return cart


@login_required
def add_to_cart(request, product_id: int):
    # Add a product or increase its quantity.
    if request.user.role != 'customer':
        return HttpResponseForbidden('Only customers can place orders.')
    product = get_object_or_404(Product, pk=product_id)
    cart = _get_user_cart(request.user)
    quantity = int(request.POST.get('quantity', 1))
    variation_id = request.POST.get('variation')
    variation = None
    if variation_id:
        variation = get_object_or_404(Variation, pk=variation_id, product=product)
    if variation:
        if variation.stock < quantity:
            messages.error(request, 'Not enough stock for this variation.')
            return redirect('product_detail', product_id=product.id)
    else:
        if product.stock < quantity:
            messages.error(request, 'Not enough stock for this product.')
            return redirect('product_detail', product_id=product.id)
    cart.add_product(product, quantity, variation)
    messages.success(request, f'{product.name} added to your shopping cart.')
    if variation:
        return redirect(f"{redirect('view_cart').url}?variation={variation.id}")
    return redirect('view_cart')


@login_required
def buy_now(request, product_id: int):
    # Add a product then jump straight to checkout.
    if request.user.role != 'customer':
        return HttpResponseForbidden('Only customers can place orders.')
    product = get_object_or_404(Product, pk=product_id)
    cart = _get_user_cart(request.user)
    quantity = int(request.POST.get('quantity', 1))
    variation_id = request.POST.get('variation')
    variation = None
    if variation_id:
        variation = get_object_or_404(Variation, pk=variation_id, product=product)
    if variation:
        if variation.stock < quantity:
            messages.error(request, 'Not enough stock for this variation.')
            return redirect('product_detail', product_id=product.id)
    else:
        if product.stock < quantity:
            messages.error(request, 'Not enough stock for this product.')
            return redirect('product_detail', product_id=product.id)
    cart.add_product(product, quantity, variation)
    return redirect('delivery_confirm')


@login_required
def view_cart(request):
    # Render cart with totals.
    if request.user.role != 'customer':
        return HttpResponseForbidden('Only customers can place orders.')
    cart = _get_user_cart(request.user)
    items = cart.items.select_related('product').all()
    return render(request, 'cart/cart.html', {'cart': cart, 'items': items})


@login_required
def update_cart_item(request, product_id: int):
    # Update quantity or remove if zero.
    if request.user.role != 'customer':
        return HttpResponseForbidden('Only customers can place orders.')
    product = get_object_or_404(Product, pk=product_id)
    cart = _get_user_cart(request.user)
    quantity = int(request.POST.get('quantity', 1))
    variation_id = request.POST.get('variation')
    variation = Variation.objects.filter(pk=variation_id, product=product).first() if variation_id else None
    cart.update_item(product, quantity, variation)
    return redirect('view_cart')


@login_required
def remove_from_cart(request, product_id: int):
    # Remove a product from the cart.
    if request.user.role != 'customer':
        return HttpResponseForbidden('Only customers can place orders.')
    product = get_object_or_404(Product, pk=product_id)
    cart = _get_user_cart(request.user)
    variation_id = request.POST.get('variation')
    variation = Variation.objects.filter(pk=variation_id, product=product).first() if variation_id else None
    cart.remove_product(product, variation)
    return redirect('view_cart')


@login_required
def delivery_info(request, product_id: int):
    if request.user.role != 'customer':
        return HttpResponseForbidden('Only customers can place orders.')
    product = get_object_or_404(Product, pk=product_id)
    cart = _get_user_cart(request.user)
    variations = product.variations.filter(is_active=True)
    selected_variation = None
    variation_id = request.GET.get('variation')
    if variation_id:
        selected_variation = variations.filter(pk=variation_id).first()
    return render(
        request,
        'cart/delivery_info.html',
        {
            'product': product,
            'cart': cart,
            'variations': variations,
            'selected_variation': selected_variation,
        },
    )

# Create your views here.
