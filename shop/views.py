from django.shortcuts import render
from django.http import HttpResponse, Http404
from .models import Product, Category

def home(request):
   all_products = Product.objects.all()[:8]
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
   all_products = Product.objects.all()

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
      half_star = rate - full_star >= 0.5

      prod.full_star = full_star
      prod.half_star = half_star
      prod.star_range = range(5)
