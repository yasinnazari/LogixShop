from django.contrib import admin
from django.conf.urls.static import static
from django.urls import path, include
from shop.views import home, about, products
from . import settings

urlpatterns = [
    path('admin/', admin.site.urls, name="admin"),
    path('', home, name="home"),
    path('about/', about, name="about"),
    path('products/', products, name="products"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_URL)
