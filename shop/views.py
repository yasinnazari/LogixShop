from django.shortcuts import render
from django.http import HttpResponse, Http404

def hellow(request):
   return render(request, template_name="./index.html")

def products(request):
   return HttpResponse('<h1>Products</h1><ul><li>Laptop</li><li>Computer</li></ul>')
