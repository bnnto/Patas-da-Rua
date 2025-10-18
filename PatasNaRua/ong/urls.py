from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('cadastro-pet/', views.cadpet_page, name='cadpet_page'),
    path('api/cadpet/', views.cadpet_view, name='cadpet_api'),
    path('infopet-ong/', views.infopet_ong, name='infopet_ong'),
    path('localpet-ong/', views.localpet_ong, name='localpet_ong'),
    path('pet/<int:pet_id>/editar/', views.editar_pet, name='editar_pet'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)