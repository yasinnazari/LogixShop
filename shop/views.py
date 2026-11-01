from django.shortcuts import render
from django.http import HttpResponse, Http404
from django.db.models import Prefetch
from .models import Category, Product, ProductImage


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


def login(request):
   return render(request, './main/login.html')


def calculate_rating(all_products):
   for prod in all_products:
      rate = prod.rating
      full_star = int(rate)
      half_star = rate - full_star > 0.4

      prod.full_star = full_star
      prod.half_star = half_star
      prod.star_range = range(5)
