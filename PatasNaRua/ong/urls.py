from django.urls import path
from . import views

urlpatterns = [
    path('cadpet/', views.cadpet_view, name='cadpet'),
]