from .models import Cart


def cart_item_count(request):
    if not request.user.is_authenticated:
        return {'cart_item_count': 0}
    cart, _created = Cart.objects.get_or_create(user=request.user)
    return {'cart_item_count': cart.items.count()}
