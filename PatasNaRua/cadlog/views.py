from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.views.decorators.cache import never_cache
from django.utils import timezone
from datetime import timedelta
from .models import CustomUser, ONG, UsuarioComum
import re

login_attempts = {}

def validar_cpf(cpf):
    cpf = re.sub(r'[^0-9]', '', cpf)
    
    if len(cpf) != 11:
        return False
    
    if cpf == cpf[0] * 11:
        return False
    
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto
    
    if int(cpf[9]) != digito1:
        return False
    
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto
    
    return int(cpf[10]) == digito2

def validar_cnpj(cnpj):
    cnpj = re.sub(r'[^0-9]', '', cnpj)
    
    if len(cnpj) != 14:
        return False
    
    if cnpj == cnpj[0] * 14:
        return False
    
    multiplicadores1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * multiplicadores1[i] for i in range(12))
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto
    
    if int(cnpj[12]) != digito1:
        return False
    
    multiplicadores2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * multiplicadores2[i] for i in range(13))
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto
    
    return int(cnpj[13]) == digito2

def validar_email_formato(email):
    try:
        validate_email(email)
        return True
    except ValidationError:
        return False
    
def verificar_rate_limit(identificador, max_tentativas=5, janela_tempo=15):
    cache_key = f'rate_limit_{identificador}'
    tentativas = cache.get(cache_key, [])
    agora = timezone.now()
    
    tentativas = [t for t in tentativas if agora - t < timedelta(minutes=janela_tempo)]
    
    if len(tentativas) >= max_tentativas:
        return False, tentativas[0] + timedelta(minutes=janela_tempo)
    
    return True, None

def registrar_tentativa(identificador):
    cache_key = f'rate_limit_{identificador}'
    tentativas = cache.get(cache_key, [])
    tentativas.append(timezone.now())
    cache.set(cache_key, tentativas, 60 * 30)

def limpar_tentativas(identificador):
    cache_key = f'rate_limit_{identificador}'
    cache.delete(cache_key)

def validar_telefone(telefone):
    telefone_limpo = re.sub(r'[^0-9]', '', telefone)
    return len(telefone_limpo) in [10, 11] and telefone_limpo[:2].isdigit()

@never_cache
def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        senha = request.POST.get('senha')
        lembrar = request.POST.get('lembrar')

        if not validar_email_formato(email):
            messages.error(request, 'Formato de email inválido')
            return render(request, 'login.html')

        ip_address = request.META.get('REMOTE_ADDR')
        identificador_ip = f"ip_{ip_address}"
        identificador_email = f"email_{email}"

        pode_tentar_ip, tempo_liberacao_ip = verificar_rate_limit(identificador_ip)
        pode_tentar_email, tempo_liberacao_email = verificar_rate_limit(identificador_email)

        if not pode_tentar_ip:
            tempo_restante = int((tempo_liberacao_ip - timezone.now()).total_seconds() / 60)
            messages.error(request, f'Muitas tentativas. Tente novamente em {tempo_restante} minutos.')
            return render(request, 'login.html')
        
        if not pode_tentar_email:
            tempo_restante = int((tempo_liberacao_email - timezone.now()).total_seconds() / 60)
            messages.error(request, f'Muitas tentativas para este email. Tente novamente em {tempo_restante} minutos.')
            return render(request, 'login.html')

        user = authenticate(request, username=email, password=senha)

        if user is not None:
            limpar_tentativas(identificador_ip)
            limpar_tentativas(identificador_email)

            login(request, user)

            if not lembrar:
                request.session.set_expiry(0)
            else:
                request.session.set_expiry(2592000)

            if hasattr(user, 'ong'):
                messages.success(request, f'Bem-vinda, {user.ong.nome_ong}!')
                return redirect('cadastro')
            elif hasattr(user, 'usuario_comum'):
                messages.success(request, f'Bem-vindo(a), {user.first_name}!')
                return redirect('cadpet_page')
            else:
                messages.warning(request, 'Perfil incompleto.')
                return redirect('login')
        else:
            registrar_tentativa(identificador_ip)
            registrar_tentativa(identificador_email)
            messages.error(request, 'Email ou senha incorretos')
    
    return render(request, 'login.html')

def cadastro_usuario(request):
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        cpf = request.POST.get('cpf', '').strip()
        email = request.POST.get('email', '').strip()
        telefone = request.POST.get('telefone', '').strip()
        data_nascimento = request.POST.get('data_nascimento')
        endereco = request.POST.get('endereco', '').strip()
        senha = request.POST.get('senha')
        confirma_senha = request.POST.get('confirma_senha')

        if not validar_email_formato(email):
            messages.error(request, 'Formato de email inválido')
            return render(request, 'cadastro_usuario.html')
        
        if not validar_cpf(cpf):
            messages.error(request, 'CPF inválido')
            return render(request, 'cadastro_usuario.html')
        
        if not validar_telefone(telefone):
            messages.error(request, 'Telefone inválido. Use o formato (XX) XXXXX-XXXX')
            return render(request, 'cadastro_usuario.html')
        
        if senha != confirma_senha:
            messages.error(request, 'As senhas não coincidem')
            return render(request, 'cadastro_usuario.html')
        
        if len(senha) < 8:
            messages.error(request, 'A senha deve ter no mínimo 8 caracteres')
            return render(request, 'cadastro_usuario.html')
        
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, 'Este email já está cadastrado.')
            return render(request, 'cadastro_usuario.html')
        
        cpf_limpo = re.sub(r'[^0-9]', '', cpf)
        if UsuarioComum.objects.filter(cpf=cpf_limpo).exists():
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
        nome_ong = request.POST.get('nome_ong', '').strip()
        cnpj = request.POST.get('cnpj', '').strip()
        endereco = request.POST.get('endereco', '').strip()
        email_institucional = request.POST.get('email_institucional', '').strip()
        nome_responsavel = request.POST.get('nome_responsavel', '').strip()
        cpf_responsavel = request.POST.get('cpf_responsavel', '').strip()
        telefone = request.POST.get('telefone', '').strip()
        senha = request.POST.get('senha')
        confirma_senha = request.POST.get('confirma_senha')

        if not all([nome_ong, cnpj, endereco, email_institucional, nome_responsavel, cpf_responsavel, telefone, senha]):
            messages.error(request, 'Todos os campos são obrigatórios!')
            return render(request, 'cadastro_ong.html')
        
        if not validar_email_formato(email_institucional):
            messages.error(request, 'Formato de email inválido')
            return render(request, 'cadastro_ong.html')
        
        if not validar_cnpj(cnpj):
            messages.error(request, 'CNPJ inválido')
            return render(request, 'cadastro_ong.html')
        
        if not validar_cpf(cpf_responsavel):
            messages.error(request, 'CPF do responsável inválido')
            return render(request, 'cadastro_ong.html')
        
        if not validar_telefone(telefone):
            messages.error(request, 'Telefone inválido. Use o formato (XX) XXXXX-XXXX')
            return render(request, 'cadastro_ong.html')
        
        if senha != confirma_senha:
            messages.error(request, 'As senhas não coincidem')
            return render(request, 'cadastro_ong.html')
        
        if len(senha) < 8:
            messages.error(request, 'A senha deve ter no mínimo 8 caracteres!')
            return render(request, 'cadastro_ong.html')
        
        if CustomUser.objects.filter(email=email_institucional).exists():
            messages.error(request, 'Este email já está cadastrado.')
            return render(request, 'cadastro_ong.html')
        
        cnpj_limpo = re.sub(r'[^0-9]', '', cnpj)
        if ONG.objects.filter(cnpj=cnpj_limpo).exists():
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

            cpf_limpo = re.sub(r'[^0-9]', '', cpf_responsavel)

            ONG.objects.create(
                user=user,
                nome_ong=nome_ong,
                cnpj=cnpj_limpo,
                endereco=endereco,
                email_institucional=email_institucional,
                nome_responsavel=nome_responsavel,
                cpf_responsavel=cpf_limpo
            )

            messages.success(request, 'ONG cadastrada com sucesso! Faça Login')
            return redirect('login')
        
        except Exception as e:
            messages.error(request, f'Erro ao fazer cadastro: {str(e)}')
            return render(request, 'cadastro_ong.html')
    
    return render(request, 'cadastro_ong.html')

def cadastro_escolha(request):
    return render(request, 'cadastro_escolha.html')

@never_cache
def esqueci_senha(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()

        if not validar_email_formato(email):
            messages.info(request, 'Se o email estiver cadastrado, você receberá instruções de recuperação.')
            return redirect('login')
        
        ip_address = request.META.get('REMOTE_ADDR')
        identificador = f"recuperacao_{ip_address}"
        
        pode_tentar, tempo_liberacao = verificar_rate_limit(identificador, max_tentativas=3, janela_tempo=30)
        
        if not pode_tentar:
            tempo_restante = int((tempo_liberacao - timezone.now()).total_seconds() / 60)
            messages.error(request, f'Muitas tentativas de recuperação. Tente novamente em {tempo_restante} minutos.')
            return redirect('login')
        
        registrar_tentativa(identificador)

        try:
            user = CustomUser.objects.get(email=email)
            messages.success(request, 'Se o email estiver cadastrado, você receberá instruções de recuperação')
        except CustomUser.DoesNotExist:
            messages.success(request, 'Se o email estiver cadastrado, você receberá instruções de recuperação')
        return redirect('login')
    return redirect('login')