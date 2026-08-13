from django.shortcuts import render
from django.http import HttpResponse, Http404
from .models import Product, Category

def home(request):
   all_products = Product.objects.all()
   all_categories = Category.objects.all()

   for prod in all_products:
      rate = prod.rating
      full_star = int(rate)
      half_star = rate - full_star >= 0.5
      empty_star = 5 - full_star - int(half_star)

      prod.full_star = full_star
      prod.half_star = half_star
      prod.star_range = range(5)

   context = {
      'products': all_products,
      'categories': all_categories
   }

   return render(request, "./main/home.html", context)

