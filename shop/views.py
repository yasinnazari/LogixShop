from django.shortcuts import render
from django.http import HttpResponse, Http404
from .models import Product, Category

def home(request):
   all_products = Product.objects.all()
   all_categories = Category.objects.all()

   context = {
      'products': all_products,
      'categories': all_categories
   }

   return render(request, "./index.html", context)
