from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache
from django.contrib.auth import authenticate, login
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from .models import CustomUser, ONG, UsuarioComum
from datetime import timedelta, date, datetime
from django.shortcuts import render, redirect
from django.core.mail import send_mail
from django.contrib import messages
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from django.conf import settings
import logging
import secrets
import string
import re

logger = logging.getLogger(__name__)

SENHAS_COMUNS = [
    '12345678', '123456789', '1234567890', 'password', 'senha123',
    'qwerty123', 'abc12345', '11111111', '00000000', 'password123'
]

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

def validar_data_nascimento(data_nascimento):
    try:
        data = datetime.strptime(data_nascimento, '%Y-%m-%d').date()
        idade = (date.today() - data).days // 365
        
        if idade < 18:
            return False, 'Você deve ter pelo menos 18 anos'
        if idade > 120:
            return False, 'Data de nascimento inválida'
            
        return True, ''
    except ValueError:
        return False, 'Formato de data inválido'

def validar_senha_segura(senha):
    if len(senha) < 8:
        return False, 'A senha deve ter no mínimo 8 caracteres'
    
    if senha.lower() in SENHAS_COMUNS:
        return False, 'Esta senha é muito comum. Escolha outra'
    
    tem_letra = bool(re.search(r'[a-zA-Z]', senha))
    tem_numero = bool(re.search(r'\d', senha))
    tem_especial = bool(re.search(r'[^a-zA-Z0-9]', senha))
    
    if not (tem_letra and tem_numero and tem_especial):
        return False, 'A senha deve conter letras, números e pelo menos um caracter especial'
    
    return True, ''

def verificar_rate_limit(identificador, max_tentativas=5, janela_tempo=15):
    cache_key = f'rate_limit_{identificador}'
    tentativas = cache.get(cache_key, [])
    agora = timezone.now()
    
    tentativas = [t for t in tentativas if agora - t < timedelta(minutes=janela_tempo)]
    
    if len(tentativas) >= max_tentativas:
        tempo_liberacao = tentativas[0] + timedelta(minutes=janela_tempo)
        tentativas_restantes = 0
        return False, tempo_liberacao, tentativas_restantes
    
    tentativas_restantes = max_tentativas - len(tentativas) - 1
    return True, None, tentativas_restantes

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

def gerar_codigo_recuperacao():
    return ''.join(secrets.choice(string.digits) for _ in range(6))

def enviar_email_recuperacao(email, codigo):
    assunto = 'Recuperação de senha'
    mensagem = f"""
    Olá
    Você solicitou a recuperação de senha.

    Seu codigo de verificação é: {codigo}

    Este código expira em 15 minutos

    Se você não solicitou esta recuperação, ignore este email.

    Atenciosamente,
    Patas na Rua
    """

    try:
        resultado = send_mail(
            assunto,
            mensagem,
            settings.EMAIL_HOST_USER,
            [email],
            fail_silently=False,
        )
        if resultado == 1:
            logger.info(f'Email de recuperação enviado com sucesso para {email}')
            return True
        else:
            logger.error(f'Falha ao enviar email para {email}')
            return False
    except Exception as e:
        logger.error(f"Erro ao enviar email para {email}: {str(e)}")
        return False

@never_cache
@require_http_methods(["GET", "POST"])
@csrf_protect
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

        pode_tentar_ip, tempo_liberacao_ip, _ = verificar_rate_limit(identificador_ip)
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
            logger.warning(f'Tentativa de login falha para {email} do IP {ip_address}')
            messages.error(request, 'Email ou senha incorretos')
    
    return render(request, 'login.html')

@transaction.atomic
def cadastro_usuario(request):
    if request.method == 'POST':
        ip_address = request.META.get('REMOTE_ADDR')
        identificador = f"cadastro_{ip_address}"
        
        pode_tentar, tempo_liberacao, _ = verificar_rate_limit(
            identificador, max_tentativas=5, janela_tempo=60
        )
        
        if not pode_tentar:
            tempo_restante = int((tempo_liberacao - timezone.now()).total_seconds() / 60)
            messages.error(request, f'Muitos cadastros. Tente novamente em {tempo_restante} minutos.')
            return render(request, 'cadastro_usuario.html')

        nome = request.POST.get('nome', '').strip()
        cpf = request.POST.get('cpf', '').strip()
        email = request.POST.get('email', '').strip()
        telefone = request.POST.get('telefone', '').strip()
        data_nascimento = request.POST.get('data_nascimento')
        endereco = request.POST.get('endereco', '').strip()
        senha = request.POST.get('senha')
        confirma_senha = request.POST.get('confirma_senha')

        campos_obrigatorios = {
            'nome': nome,
            'cpf': cpf,
            'email': email,
            'telefone': telefone,
            'data_nascimento': data_nascimento,
            'endereco': endereco,
            'senha': senha
        }

        campos_vazios = [campo for campo, valor in campos_obrigatorios.items() if not valor]
        if campos_vazios:
            messages.error(request, 'Todos os campos são obrigatórios')
            return render(request, 'cadastro_usuario.html')

        if not validar_email_formato(email):
            messages.error(request, 'Formato de email inválido')
            return render(request, 'cadastro_usuario.html')
        
        valido, mensagem = validar_data_nascimento(data_nascimento)
        if not valido:
            messages.error(request, mensagem)
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
        
        valido, mensagem = validar_senha_segura(senha)
        if not valido:
            messages.error(request, mensagem)
            return render(request, 'cadastro_usuario.html')
        
        if CustomUser.objects.filter(email__iexact=email).exists():
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

            registrar_tentativa(identificador)
            logger.info(f'Novo usuário cadastrado: {email}')
            messages.success(request, 'Cadastro realizado com sucesso! Faça login!')
            return redirect('login')
        
        except Exception as e:
            messages.error(request, f'Erro ao criar cadastro {str(e)}')
            return render(request, 'cadastro_usuario.html')
        
    return render(request, 'cadastro_usuario.html')

@transaction.atomic
def cadastro_ong(request):
    if request.method == 'POST':
        ip_address = request.META.get('REMOTE_ADDR')
        identificador = f"cadastro_{ip_address}"
        
        pode_tentar, tempo_liberacao, _ = verificar_rate_limit(
            identificador, max_tentativas=5, janela_tempo=60
        )
        
        if not pode_tentar:
            tempo_restante = int((tempo_liberacao - timezone.now()).total_seconds() / 60)
            messages.error(request, f'Muitos cadastros. Tente novamente em {tempo_restante} minutos.')
            return render(request, 'cadastro_usuario.html')

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
        
        valido, mensagem = validar_senha_segura(senha)
        if not valido:
            messages.error(request, mensagem)
            return render(request, 'cadastro_ong.html')
        
        if CustomUser.objects.filter(email__iexact=email_institucional).exists():
            messages.error(request, 'Este email já está cadastrado.')
            return render(request, 'cadastro_ong.html')
        
        cnpj_limpo = re.sub(r'[^0-9]', '', cnpj)
        if ONG.objects.filter(cnpj=cnpj_limpo).exists():
            messages.error(request, 'Este CNPJ já está cadastrado.')
            return render(request, 'cadastro_ong.html')
        
        if ONG.objects.filter(email_institucional__iexact=email_institucional).exists():
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
            
            registrar_tentativa(identificador)
            logger.info(f'Novo usuário cadastrado: {email_institucional}')
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
            return render(request, 'esqueci_senha.html')
        
        ip_address = request.META.get('REMOTE_ADDR')
        identificador = f"recuperacao_{ip_address}"
        
        pode_tentar, tempo_liberacao = verificar_rate_limit(identificador, max_tentativas=3, janela_tempo=30)
        
        if not pode_tentar:
            tempo_restante = int((tempo_liberacao - timezone.now()).total_seconds() / 60)
            messages.error(request, f'Muitas tentativas de recuperação. Tente novamente em {tempo_restante} minutos.')
            return render(request, 'esqueci_senha.html')
        
        registrar_tentativa(identificador)

        try:
            user = CustomUser.objects.get(email=email)

            codigo = gerar_codigo_recuperacao()

            cache_key = f'codigo_recuperacao_{email}'
            cache.set(cache_key, codigo, 60 * 15)

            if enviar_email_recuperacao(email, codigo):
                logger.info(f'Solicitação de recuperação de senha para {email} do IP {ip_address}')
                messages.success(request, 'Código de verificação enviado para seu email.')
                return redirect('verificar_codigo', email=email)
            else:
                messages.error(request, 'Erro ao enviar email. Tente novamente')
                return render(request, 'esqueci_senha.html')

        except CustomUser.DoesNotExist:
            messages.success(request, 'Se o email estiver cadastrado, você receberá instruções de recuperação')

        return render(request, 'esqueci_senha.html')
    
    return render(request, 'esqueci_senha.html')

## @login_required # DESCOMENTAR DEPOIS DE TODOS TESTES DE HTML/CSS
@never_cache
def verificar_codigo(request, email):
    if request.method == 'POST':
        codigo_digitado = request.POST.get('codigo', '').strip()

        if not codigo_digitado:
            messages.error(request, 'Digite o código recebido por email.')
            return render(request, 'verificar_codigo.html', {'email': email})
    
        ip_address = request.META.get('REMOTE_ADDR')
        identificador = f"verificacao_{ip_address}_{email}"
        
        pode_tentar, tempo_liberacao = verificar_rate_limit(identificador, max_tentativas=5, janela_tempo=15)
        
        if not pode_tentar:
            tempo_restante = int((tempo_liberacao - timezone.now()).total_seconds() / 60)
            messages.error(request, f'Muitas tentativas. Tente novamente em {tempo_restante} minutos.')
            return render(request, 'verificar_codigo.html', {'email': email})
        
        registrar_tentativa(identificador)

        cache_key = f'codigo_recuperacao_{email}'
        codigo_armazenado = cache.get(cache_key)

        if not codigo_armazenado:
            messages.error(request, 'Código expirado. Solicite um novo código')
            return redirect('esqueci_senha')
        
        if codigo_digitado == codigo_armazenado:
            limpar_tentativas(identificador)
            cache.set(f'email_verificado_{email}', True, 60 * 30)
            messages.success(request, 'Código verificado! Defina sua nova senha.')
            return redirect('redefinir_senha', email=email)
        else:
            messages.error(request, 'Código incorreto. Tente novamente.')
    
    return render(request, 'verificar_codigo.html', {'email': email})

## @login_required # DESCOMENTAR DEPOIS DE TODOS TESTES DE HTML/CSS
@never_cache
def redefinir_senha(request, email):
    if not cache.get(f'email_verificado_{email}'):
        messages.error(request, 'Sessão expirada. Solicite uma nova recuperação.')
        return redirect('esqueci_senha')
    
    if request.method == 'POST':
        nova_senha = request.POST.get('nova_senha')
        confirma_senha = request.POST.get('confirma_senha')

        if not nova_senha or not confirma_senha:
            messages.error(request, 'Preencha todos os campos.')
            return render(request, 'redefinir_senha.html', {'email': email})
        
        if nova_senha != confirma_senha:
            messages.error(request, 'As senhas não coincidem.')
            return render(request, 'redefinir_senha.html', {'email': email})

        valido, mensagem = validar_senha_segura(nova_senha)
        if not valido:
            messages.error(request, mensagem)
            return render(request, 'redefinir_senha.html')
        
        try:
            user = CustomUser.objects.get(email=email)
            user.set_password(nova_senha)
            user.save()

            cache.delete(f'email_verificado_{email}')
            cache.delete(f'codigo_recuperacao_{email}')

            messages.success(request, 'Senha redefinida com sucesso! Faça login com sua nova senha.')
            return redirect('login')
        
        except CustomUser.DoesNotExist:
            messages.error(request, 'Usuário não encontrado.')
            return redirect('esqueci_senha')
    
    return render(request, 'redefinir_senha.html', {'email': email})
