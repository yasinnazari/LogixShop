from django.urls import path, include
from . import views

app_name = 'shop'

urlpatterns = [
   path('', views.home, name="home"),
   path('about', views.about, name="about"),
   path('products', views.products, name="products"),
]
