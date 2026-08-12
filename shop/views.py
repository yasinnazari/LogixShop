from django.shortcuts import render
from django.http import HttpResponse, Http404
from .models import Product

def home(request):
   all_products = Product.objects.all()
   all_products_context = {
      'products': all_products
   }

   return render(request, "./index.html", all_products_context)
