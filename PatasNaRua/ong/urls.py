from django.urls import path
from . import views

urlpatterns = [
    path('cadpet/', views.cadpet_page, name='cadpet_page'),
    path('api/cadpet', views.cadpet_view, name='cadpet_api')
]