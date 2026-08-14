from django.contrib import admin
from django.conf.urls.static import static
from django.urls import path, include
from shop.views import home, about
from . import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home),
    path('about/', about),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_URL)
