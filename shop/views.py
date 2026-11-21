from django.shortcuts import render
from django.http import HttpResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Prefetch
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST
from .models import Cart, CartItem, Category, Product, ProductImage


def products_with_primary_images(queryset=None):
   queryset = queryset if queryset is not None else Product.objects.all()
   return queryset.prefetch_related(
      Prefetch(
         'images',
         queryset=ProductImage.objects.filter(is_primary=True),
         to_attr='primary_images',
      )
   )

def home(request):
   all_products = products_with_primary_images()[:8]
   all_categories = Category.objects.all()

   calculate_rating(all_products)

   context = {
      'products': all_products,
      'categories': all_categories,
      'show_view_all': True
   }

   return render(request, "./main/home.html", context)


def about(request):
   return render(request, './main/about.html')


def products(request):
   all_products = products_with_primary_images()

   calculate_rating(all_products)

   context = {
      'products': all_products
   }

   return render(request, './main/products_list.html', context)


def product_detail(request, product_id):
   product = get_object_or_404(
      Product.objects.prefetch_related(
         Prefetch('images', queryset=ProductImage.objects.all(), to_attr='detail_images')
      ),
      pk=product_id,
   )
   calculate_rating([product])

   return render(request, './main/product_detail.html', {'product': product})


def _cart_data(user):
   cart = (
      Cart.objects.filter(user=user, status=Cart.Status.ACTIVE)
      .prefetch_related('items__product')
      .first()
   )
   items = []
   total_quantity = 0

   if cart:
        for item in cart.items.all():
            image = item.product.images.filter(is_primary=True).first() or item.product.images.first()
            items.append({
                'product_id': item.product_id,
                'name': item.product.title,
                'price': str(item.product.effective_price),
                'quantity': item.quantity,
                'image_url': image.image.url if image and image.image else '',
            'remove_url': reverse('shop:remove_from_cart', kwargs={'product_id': item.product_id}),
            })
            total_quantity += item.quantity

   return {'items': items, 'total_quantity': total_quantity}


@require_GET
def cart_summary(request):
   if not request.user.is_authenticated:
      return JsonResponse({'items': [], 'total_quantity': 0})

   return JsonResponse(_cart_data(request.user))


@require_POST
def add_to_cart(request, product_id):
   if not request.user.is_authenticated:
      return JsonResponse({'error': 'Please sign in to add products to your cart.'}, status=401)

   try:
      requested_quantity = max(1, int(request.POST.get('quantity', 1)))
   except (TypeError, ValueError):
      requested_quantity = 1

   with transaction.atomic():
      product = get_object_or_404(Product.objects.select_for_update(), pk=product_id)
      if not product.has_stock or product.stock < 1:
         return JsonResponse({'error': 'This product is currently out of stock.'}, status=409)
      if requested_quantity > product.stock:
         return JsonResponse({'error': f'Only {product.stock} item(s) available.'}, status=409)

      cart, _ = Cart.objects.get_or_create(user=request.user, status=Cart.Status.ACTIVE)
      item, created = CartItem.objects.select_for_update().get_or_create(
         cart=cart,
         product=product,
         defaults={'quantity': requested_quantity},
      )

      if not created:
         new_quantity = item.quantity + requested_quantity
         if new_quantity > product.stock:
            return JsonResponse({'error': f'Only {product.stock} item(s) available.'}, status=409)
         item.quantity = new_quantity
         item.save(update_fields=['quantity', 'updated_at'])

   return JsonResponse(_cart_data(request.user))


@require_POST
def remove_from_cart(request, product_id):
   if not request.user.is_authenticated:
      return JsonResponse({'error': 'Please sign in to manage your cart.'}, status=401)

   with transaction.atomic():
      item = get_object_or_404(
         CartItem.objects.select_for_update(),
         cart__user=request.user,
         cart__status=Cart.Status.ACTIVE,
         product_id=product_id,
      )
      item.delete()

   return JsonResponse(_cart_data(request.user))


def calculate_rating(all_products):
    for prod in all_products:
        rate = prod.rating
        full_star = int(rate)
        half_star = rate - full_star > 0.4

        prod.full_star = full_star
        prod.half_star = half_star
        prod.star_range = range(5)
