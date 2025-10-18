from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('tela-user/', views.tela_user_page, name='tela_user_page'),
    path('pet/<int:pet_id>/', views.detalhes_pet, name='detalhes_pet'),
]