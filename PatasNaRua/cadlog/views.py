from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
import json

User = get_user_model()

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        if email == 'emailinstitucional@gmail.com' and password == 'senhaong123':
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                user = User.objects.create_user(
                    username='ong_admin',
                    email=email,
                    password=password
                )
            
            # Fazer login
            user = authenticate(request, email=email, password=password)
            if user:
                login(request, user)
                messages.success(request, 'Login ONG realizado com sucesso!')
                return redirect('cadpet')

        user = authenticate(request, email=email, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, 'Login realizado com sucesso!')
            return redirect('cadpet')
        else:
            messages.error(request, 'Email ou senha incorretos!')

    return render(request, 'login.html')

def cadastro_view(request):
    return render(request, 'cadastro.html')
