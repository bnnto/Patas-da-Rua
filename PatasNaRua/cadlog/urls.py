from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('esqueci-senha/', views.esqueci_senha, name='esqueci_senha'),
    path('verificar-codigo/<str:email>/<str:token>/', views.verificar_codigo, name='verificar_codigo'),
    path('redefinir-senha/<str:email>/<str:token>/', views.redefinir_senha, name='redefinir_senha'),
    path('cadastro/', views.cadastro_escolha, name='cadastro_escolha'),
    path('cadastro/ong/', views.cadastro_ong, name='cadastro_ong'),
    path('cadastro/usuario/', views.cadastro_usuario, name='cadastro_usuario'),
]