from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('cadpet/', views.cadpet_page, name='cadpet_page'),
    path('api/cadpet/', views.cadpet_view, name='cadpet_api')
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)