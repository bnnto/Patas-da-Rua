from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('app_initial.urls')),
    path('', include('cadlog.urls')),
    path('', include('ong.urls')),
]
