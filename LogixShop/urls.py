from django.contrib import admin
from django.conf.urls.static import static
from django.urls import path, include
from . import settings

urlpatterns = [
    path('admin/', admin.site.urls, name="admin"),
    path('', include('shop.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_URL)
