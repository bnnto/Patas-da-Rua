from django.urls import path
from django.views.generic import TemplateView
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('esqueci-senha/', views.esqueci_senha, name='esqueci_senha'),
    path('verificar-codigo/<str:email>/', views.verificar_codigo, name='verificar_codigo'),
    path('redefinir-senha/<str:email>/', views.redefinir_senha, name='redefinir_senha'),
    path('cadastro/', views.cadastro_escolha, name='cadastro_escolha'),
    path('cadastro/ong/', views.cadastro_ong, name='cadastro_ong'),
    path('cadastro/usuario/', views.cadastro_usuario, name='cadastro_usuario'),
    path('testar/redefinir-senha/', TemplateView.as_view(template_name='redefinir_senha.html')),
]
