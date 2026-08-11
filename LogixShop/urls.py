from django.contrib import admin
from django.conf.urls.static import static
from django.urls import path, include
from shop.views import hellow
from . import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('shop/', include("shop.urls"), name='shop'),
    path('', hellow),
]+static(settings.MEDIA_URL, document_root=settings.MEDIA_URL)
