from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages
from .models import CustomUser, ONG, UsuarioComum

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        senha = request.POST.get('senha')

        user = authenticate(request, username=email, password=senha)

        if user is not None:
            login(request, user)

            if hasattr(user, 'ong'):
                messages.success(request, f'Bem-vinda, {user.ong.nome_ong}!')
                return redirect('cadastro')
            elif hasattr(user, 'usuario_comum'):
                messages.success(request, f'Bem-vindo(a), {user.first_name}!')
                return redirect('cadpet_page')
            else:
                messages.warning(request, 'Perfil incompleto.')
                return redirect('')
        else:
            messages.error(request, 'Email ou senha incorretos')
    
    return render(request, 'login.html')

def cadastro_usuario(request):
    if request.method == 'POST':
        nome = request.POST.get('nome')
        cpf = request.POST.get('cpf')
        email = request.POST.get('email')
        telefone = request.POST.get('telefone')
        data_nascimento = request.POST.get('data_nascimento')
        endereco = request.POST.get('endereco')
        senha = request.POST.get('senha')
        confirma_senha = request.POST.get('confirma_senha')

        if senha != confirma_senha:
            messages.error(request, 'As senhas não coincidem')
            return render(request, 'cadastro_usuario.html')
        
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, 'Este email ja está cadastrado.')
            return render(request, 'cadastro_usuario.html')
        
        if UsuarioComum.objects.filter(cpf=cpf).exists():
            messages.error(request, 'Este CPF já está cadastrado.')
            return render(request, 'cadastro_usuario.html')
        
        try:
            nome_split = nome.split()
            first_name = nome_split[0] if nome_split else ''
            last_name = ' '.join(nome_split[1:]) if len(nome_split) > 1 else ''

            user = CustomUser.objects.create_user(
                username=email,
                email=email,
                password=senha,
                first_name=first_name,
                last_name=last_name,
                telefone=telefone
            )

            UsuarioComum.objects.create(
                user=user,
                cpf=cpf,
                data_nascimento=data_nascimento,
                endereco=endereco
            )

            messages.success(request, 'Cadastro realizado com sucesso! Faça login!')
            return redirect('login')
        
        except Exception as e:
            messages.error(request, f'Erro ao criar cadastro {str(e)}')
            return render(request, 'cadastro_usuario.html')
        
    return render(request, 'cadastro_usuario.html')

def cadastro_ong(request):
    if request.method == 'POST':
        nome_ong = request.POST.get('nome_ong')
        cnpj = request.POST.get('cnpj')
        endereco = request.POST.get('endereco')
        email_institucional = request.POST.get('email_institucional')
        nome_responsavel = request.POST.get('nome_responsavel')
        cpf_responsavel = request.POST.get('cpf_responsavel')
        telefone = request.POST.get('telefone')
        senha =  request.POST.get('senha')
        confirma_senha = request.POST.get('confirma_senha')

        if not all([nome_ong, cnpj, endereco, email_institucional, nome_responsavel, cpf_responsavel, telefone, senha]):
            messages.error(request, 'Todos os campos são obrigatórios!')
            return render(request, 'cadastro_ong.html')
        
        if senha != confirma_senha:
            messages.error(request, 'As senhas não coincidem')
            return render(request, 'cadastro_ong.html')
        
        if len(senha) < 6:
            messages.error(request, 'A senha deve ter no mínimo 6 caracteres!')
            return render(request, 'cadastro_ong.html')
        
        if CustomUser.objects.filter(email=email_institucional).exists():
            messages.error(request, 'Este email ja está cadastrado.')
            return render(request, 'cadastro_ong.html')
        
        if ONG.objects.filter(cnpj=cnpj).exists():
            messages.error(request, 'Este CNPJ já está cadastrado.')
            return render(request, 'cadastro_ong.html')
        
        if ONG.objects.filter(email_institucional=email_institucional).exists():
            messages.error(request, 'Este email institucional já está cadastrado!')
            return render(request, 'cadastro_ong.html')
        
        try:
            nome_split = nome_responsavel.split()
            first_name = nome_split[0] if nome_split else ''
            last_name = ' '.join(nome_split[1:]) if len(nome_split) > 1 else ''

            user = CustomUser.objects.create_user(
                username=email_institucional,
                email=email_institucional,
                password=senha,
                first_name=first_name,
                last_name=last_name,
                telefone=telefone
            )

            ONG.objects.create(
                user=user,
                nome_ong=nome_ong,
                cnpj=cnpj,
                endereco=endereco,
                email_institucional=email_institucional,
                nome_responsavel=nome_responsavel,
                cpf_responsavel=cpf_responsavel
            )

            messages.success(request, 'ONG cadastrada com sucesso! Faça Login')
            return redirect('login')
        
        except Exception as e:
            messages.error(request, f'Erro ao fazer cadastro: {str(e)}')
            return render(request, 'cadastro_ong.html')
    
    return render(request, 'cadastro_ong.html')

def cadastro_escolha(request):
    return render(request, 'cadastro_escolha.html')