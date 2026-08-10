from django.urls import path, include
from . import views

app_name = 'shop'

urlpatterns = [
   path('', views.hellow, name="index"),
   path('products/', views.products, name="products")
]
