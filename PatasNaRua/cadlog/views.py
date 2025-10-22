from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache
from django.utils.crypto import constant_time_compare
from django.contrib.auth import authenticate, login
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from .models import CustomUser, ONG, UsuarioComum
from dateutil.relativedelta import relativedelta
from datetime import timedelta, date, datetime
from django.shortcuts import render, redirect
from django.core.mail import send_mail
from django.contrib import messages
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from functools import wraps
import dns.resolver
import logging
import secrets
import string
import re

logger = logging.getLogger(__name__)

SENHAS_COMUNS = [
    '12345678', '123456789', '1234567890', 'password', 'senha123',
    'qwerty123', 'abc12345', '11111111', '00000000', 'password123',
    'senha1234', 'admin123', '87654321', 'senha@123'
]

def requer_fluxo_recuperacao(view_func):
    @wraps(view_func)
    def wrapper(request, email, token, *args, **kwargs):
        cache_key = f'token_recuperacao_{email}'
        token_armazenado = cache.get(cache_key)
        
        if not token_armazenado:
            logger.warning(f'Tentativa de acesso sem token válido para {email} do IP {request.META.get("REMOTE_ADDR")}')
            messages.error(request, 'Sessão expirada ou inválida. Solicite uma nova recuperação.')
            return redirect('esqueci_senha')
        
        if not constant_time_compare(token, token_armazenado):
            logger.warning(f'Tentativa de acesso com token inválido para {email} do IP {request.META.get("REMOTE_ADDR")}')
            messages.error(request, 'Token inválido. Solicite uma nova recuperação.')
            return redirect('esqueci_senha')
        
        return view_func(request, email, token, *args, **kwargs)
    return wrapper

def requer_codigo_verificado(view_func):
    @wraps(view_func)
    def wrapper(request, email, token, *args, **kwargs):
        cache_key = f'email_verificado_{email}_{token}'
        if not cache.get(cache_key):
            logger.warning(f'Tentativa de redefinir senha sem verificar código para {email}')
            messages.error(request, 'Você precisa verificar o código primeiro.')
            return redirect('verificar_codigo', email=email, token=token)
        
        return view_func(request, email, token, *args, **kwargs)
    return wrapper

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

        dominio = email.split('@')[1]

        try:
            dns.resolver.resolve(dominio, 'MX')
        except dns.resolver.NXDOMAIN:
            return False
        except dns.resolver.NoAnswer:
            try:
                dns.resolver.resolve(dominio, 'A')
            except Exception:
                return False
        
        return True
    
    except ValidationError:
        return False
    except Exception:
        return False

def validar_data_nascimento(data_nascimento):
    try:
        data = datetime.strptime(data_nascimento, '%Y-%m-%d').date()
        hoje = date.today()
        idade = relativedelta(hoje, data).years
        
        if data > hoje:
            return False, 'Data de nascimento não pode ser no futuro'
        
        if idade < 18:
            return False, 'Você deve ter pelo menos 18 anos'
        
        if idade > 120:
            return False, 'Data de nascimento inválida'
            
        return True, ''
    except (ValueError, TypeError):
        return False, 'Formato de data inválido'

def validar_senha_segura(senha):
    if len(senha) < 8:
        return False, 'A senha deve ter no mínimo 8 caracteres'
    
    if len(senha) > 128:
        return False, 'A senha deve ter no máximo 128 caracteres'
    
    if senha.lower() in SENHAS_COMUNS:
        return False, 'Esta senha é muito comum. Escolha outra'
    
    tem_letra = bool(re.search(r'[a-zA-Z]', senha))
    tem_numero = bool(re.search(r'\d', senha))
    tem_especial = bool(re.search(r'[^a-zA-Z0-9]', senha))
    
    if not (tem_letra and tem_numero and tem_especial):
        return False, 'A senha deve conter letras, números e pelo menos um caractere especial'
    
    return True, ''

def validar_telefone(telefone):
    telefone_limpo = re.sub(r'[^0-9]', '', telefone)
    
    if len(telefone_limpo) not in [10, 11]:
        return False
    
    ddd = int(telefone_limpo[:2])
    if ddd < 11 or ddd > 99:
        return False
    
    return True

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

def gerar_codigo_recuperacao():
    return ''.join(secrets.choice(string.digits) for _ in range(6))

def gerar_token_recuperacao():
    return secrets.token_urlsafe(32)

def enviar_email_recuperacao(email, codigo):
    assunto = 'Recuperação de senha - Patas na Rua'
    mensagem = f"""
Olá,

Você solicitou a recuperação de senha da sua conta.

Seu código de verificação é: {codigo}

Este código expira em 15 minutos.

Se você não solicitou esta recuperação, ignore este email e sua senha permanecerá inalterada.

Atenciosamente,
Equipe Patas na Rua
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
        email = request.POST.get('email', '').strip().lower()
        senha = request.POST.get('senha')
        lembrar = request.POST.get('lembrar')

        if not email or not senha:
            messages.error(request, 'Email e senha são obrigatórios')
            return render(request, 'login.html')

        if not validar_email_formato(email):
            messages.error(request, 'Formato de email inválido')
            return render(request, 'login.html')

        ip_address = request.META.get('REMOTE_ADDR', 'unknown')
        identificador_ip = f"login_ip_{ip_address}"
        identificador_email = f"login_email_{email}"

        pode_tentar_ip, tempo_liberacao_ip, _ = verificar_rate_limit(identificador_ip)
        pode_tentar_email, tempo_liberacao_email, _ = verificar_rate_limit(identificador_email)

        if not pode_tentar_ip:
            tempo_restante = max(1, int((tempo_liberacao_ip - timezone.now()).total_seconds() / 60))
            messages.error(request, f'Muitas tentativas. Tente novamente em {tempo_restante} minutos.')
            logger.warning(f'Rate limit atingido por IP: {ip_address}')
            return render(request, 'login.html')
        
        if not pode_tentar_email:
            tempo_restante = max(1, int((tempo_liberacao_email - timezone.now()).total_seconds() / 60))
            messages.error(request, f'Muitas tentativas para este email. Tente novamente em {tempo_restante} minutos.')
            logger.warning(f'Rate limit atingido para email: {email}')
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
                logger.info(f'Login bem-sucedido: ONG {user.ong.nome_ong} ({email})')
                messages.success(request, f'Bem-vinda, {user.ong.nome_ong}!')
                return redirect('cadastro')
            elif hasattr(user, 'usuario_comum'):
                logger.info(f'Login bem-sucedido: Usuário {user.first_name} ({email})')
                messages.success(request, f'Bem-vindo(a), {user.first_name}!')
                return redirect('cadpet_page')
            else:
                logger.warning(f'Login com perfil incompleto: {email}')
                messages.warning(request, 'Perfil incompleto.')
                return redirect('login')
        else:
            registrar_tentativa(identificador_ip)
            registrar_tentativa(identificador_email)
            logger.warning(f'Tentativa de login falha para {email} do IP {ip_address}')
            messages.error(request, 'Email ou senha incorretos')
    
    return render(request, 'login.html')

@transaction.atomic
@require_http_methods(["GET", "POST"])
@csrf_protect
def cadastro_usuario(request):
    if request.method == 'POST':
        ip_address = request.META.get('REMOTE_ADDR', 'unknown')
        identificador = f"cadastro_{ip_address}"
        
        pode_tentar, tempo_liberacao, _ = verificar_rate_limit(
            identificador, max_tentativas=3, janela_tempo=30
        )
        
        if not pode_tentar:
            tempo_restante = max(1, int((tempo_liberacao - timezone.now()).total_seconds() / 60))
            messages.error(request, f'Muitas tentativas de cadastro. Tente novamente em {tempo_restante} minutos.')
            return render(request, 'cadastro_usuario.html')

        nome = request.POST.get('nome', '').strip()
        cpf = request.POST.get('cpf', '').strip()
        email = request.POST.get('email', '').strip().lower()
        telefone = request.POST.get('telefone', '').strip()
        data_nascimento = request.POST.get('data_nascimento', '').strip()
        endereco = request.POST.get('endereco', '').strip()
        senha = request.POST.get('senha', '')
        confirma_senha = request.POST.get('confirma_senha', '')

        campos_obrigatorios = {
            'nome': nome,
            'cpf': cpf,
            'email': email,
            'telefone': telefone,
            'data_nascimento': data_nascimento,
            'endereco': endereco,
            'senha': senha,
            'confirma_senha': confirma_senha
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
            messages.error(request, 'Este email já está cadastrado')
            return render(request, 'cadastro_usuario.html')
        
        cpf_limpo = re.sub(r'[^0-9]', '', cpf)
        if UsuarioComum.objects.filter(cpf=cpf_limpo).exists():
            messages.error(request, 'Este CPF já está cadastrado')
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
                cpf=cpf_limpo,
                data_nascimento=data_nascimento,
                endereco=endereco
            )

            registrar_tentativa(identificador)
            logger.info(f'Novo usuário cadastrado: {email} do IP {ip_address}')
            messages.success(request, 'Cadastro realizado com sucesso! Faça login.')
            return redirect('login')
        
        except Exception as e:
            logger.error(f'Erro ao criar cadastro para {email}: {str(e)}')
            messages.error(request, 'Erro ao processar cadastro. Tente novamente.')
            return render(request, 'cadastro_usuario.html')
        
    return render(request, 'cadastro_usuario.html')

@transaction.atomic
@require_http_methods(["GET", "POST"])
@csrf_protect
def cadastro_ong(request):
    if request.method == 'POST':
        ip_address = request.META.get('REMOTE_ADDR', 'unknown')
        identificador = f"cadastro_ong_{ip_address}"
        
        pode_tentar, tempo_liberacao, _ = verificar_rate_limit(
            identificador, max_tentativas=3, janela_tempo=30
        )
        
        if not pode_tentar:
            tempo_restante = max(1, int((tempo_liberacao - timezone.now()).total_seconds() / 60))
            messages.error(request, f'Muitas tentativas de cadastro. Tente novamente em {tempo_restante} minutos.')
            return render(request, 'cadastro_ong.html')

        nome_ong = request.POST.get('nome_ong', '').strip()
        cnpj = request.POST.get('cnpj', '').strip()
        endereco = request.POST.get('endereco', '').strip()
        email_institucional = request.POST.get('email_institucional', '').strip().lower()
        nome_responsavel = request.POST.get('nome_responsavel', '').strip()
        cpf_responsavel = request.POST.get('cpf_responsavel', '').strip()
        telefone = request.POST.get('telefone', '').strip()
        senha = request.POST.get('senha', '')
        confirma_senha = request.POST.get('confirma_senha', '')

        if not all([nome_ong, cnpj, endereco, email_institucional, nome_responsavel, cpf_responsavel, telefone, senha, confirma_senha]):
            messages.error(request, 'Todos os campos são obrigatórios')
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
            messages.error(request, 'Este email já está cadastrado')
            return render(request, 'cadastro_ong.html')
        
        cnpj_limpo = re.sub(r'[^0-9]', '', cnpj)
        if ONG.objects.filter(cnpj=cnpj_limpo).exists():
            messages.error(request, 'Este CNPJ já está cadastrado')
            return render(request, 'cadastro_ong.html')
        
        if ONG.objects.filter(email_institucional__iexact=email_institucional).exists():
            messages.error(request, 'Este email institucional já está cadastrado')
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
            logger.info(f'Nova ONG cadastrada: {nome_ong} ({email_institucional}) do IP {ip_address}')
            messages.success(request, 'ONG cadastrada com sucesso! Faça login.')
            return redirect('login')
        
        except Exception as e:
            logger.error(f'Erro ao cadastrar ONG {email_institucional}: {str(e)}')
            messages.error(request, 'Erro ao processar cadastro. Tente novamente.')
            return render(request, 'cadastro_ong.html')
    
    return render(request, 'cadastro_ong.html')

@require_http_methods(["GET"])
def cadastro_escolha(request):
    return render(request, 'cadastro_escolha.html')

@never_cache
@require_http_methods(["GET", "POST"])
@csrf_protect
def esqueci_senha(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()

        if not email:
            messages.error(request, 'Digite seu email')
            return render(request, 'esqueci_senha.html')

        if not validar_email_formato(email):
            messages.info(request, 'Se o email estiver cadastrado, você receberá instruções de recuperação.')
            return render(request, 'esqueci_senha.html')
        
        ip_address = request.META.get('REMOTE_ADDR', 'unknown')
        identificador = f"recuperacao_{ip_address}"
        
        pode_tentar, tempo_liberacao, _ = verificar_rate_limit(
            identificador, max_tentativas=3, janela_tempo=30
        )
        
        if not pode_tentar:
            tempo_restante = max(1, int((tempo_liberacao - timezone.now()).total_seconds() / 60))
            messages.error(request, f'Muitas tentativas de recuperação. Tente novamente em {tempo_restante} minutos.')
            return render(request, 'esqueci_senha.html')
        
        registrar_tentativa(identificador)

        try:
            user = CustomUser.objects.get(email__iexact=email)

            codigo = gerar_codigo_recuperacao()
            token = gerar_token_recuperacao()

            cache.set(f'codigo_recuperacao_{email}', codigo, 60 * 15)  
            cache.set(f'token_recuperacao_{email}', token, 60 * 30)    

            if enviar_email_recuperacao(email, codigo):
                logger.info(f'Solicitação de recuperação de senha para {email} do IP {ip_address}')
                messages.success(request, 'Código de verificação enviado para seu email.')
                return redirect('verificar_codigo', email=email, token=token)
            else:
                messages.error(request, 'Erro ao enviar email. Tente novamente.')
                return render(request, 'esqueci_senha.html')

        except CustomUser.DoesNotExist:
            logger.info(f'Tentativa de recuperação para email não cadastrado: {email}')
            messages.info(request, 'Se o email estiver cadastrado, você receberá instruções de recuperação.')

        return render(request, 'esqueci_senha.html')
    
    return render(request, 'esqueci_senha.html')

@never_cache
@require_http_methods(["GET", "POST"])
@csrf_protect
@requer_fluxo_recuperacao
def verificar_codigo(request, email, token):
    """View de verificação do código de recuperação"""
    if request.method == 'POST':
        codigo_digitado = request.POST.get('codigo', '').strip()

        if not codigo_digitado:
            messages.error(request, 'Digite o código recebido por email.')
            return render(request, 'verificar_codigo.html', {'email': email, 'token': token})
    
        ip_address = request.META.get('REMOTE_ADDR', 'unknown')
        identificador = f"verificacao_{ip_address}_{email}"
        
        pode_tentar, tempo_liberacao, tentativas_restantes = verificar_rate_limit(
            identificador, max_tentativas=5, janela_tempo=15
        )
        
        if not pode_tentar:
            tempo_restante = max(1, int((tempo_liberacao - timezone.now()).total_seconds() / 60))
            messages.error(request, f'Muitas tentativas. Tente novamente em {tempo_restante} minutos.')
            logger.warning(f'Rate limit atingido na verificação de código para {email} do IP {ip_address}')
            return render(request, 'verificar_codigo.html', {'email': email, 'token': token})
        
        registrar_tentativa(identificador)

        cache_key = f'codigo_recuperacao_{email}'
        codigo_armazenado = cache.get(cache_key)

        if not codigo_armazenado:
            logger.warning(f'Código expirado para {email}')
            messages.error(request, 'Código expirado. Solicite um novo código.')
            return redirect('esqueci_senha')
        
        if constant_time_compare(codigo_digitado, codigo_armazenado):
            limpar_tentativas(identificador)
            cache.set(f'email_verificado_{email}_{token}', True, 60 * 30) 
            
            logger.info(f'Código verificado com sucesso para {email}')
            messages.success(request, 'Código verificado! Defina sua nova senha.')
            return redirect('redefinir_senha', email=email, token=token)
        else:
            logger.warning(f'Código incorreto digitado para {email} (tentativas restantes: {tentativas_restantes})')
            
            if tentativas_restantes > 0:
                messages.error(request, f'Código incorreto. Você tem {tentativas_restantes} tentativa(s) restante(s).')
            else:
                messages.error(request, 'Código incorreto. Tente novamente.')
    
    return render(request, 'verificar_codigo.html', {'email': email, 'token': token})

@never_cache
@require_http_methods(["GET", "POST"])
@csrf_protect
@requer_fluxo_recuperacao 
@requer_codigo_verificado
def redefinir_senha(request, email, token):
    if request.method == 'POST':
        nova_senha = request.POST.get('nova_senha', '')
        confirma_senha = request.POST.get('confirma_senha', '')

        if not nova_senha or not confirma_senha:
            messages.error(request, 'Preencha todos os campos.')
            return render(request, 'redefinir_senha.html', {'email': email, 'token': token})
        
        if nova_senha != confirma_senha:
            messages.error(request, 'As senhas não coincidem.')
            return render(request, 'redefinir_senha.html', {'email': email, 'token': token})

        valido, mensagem = validar_senha_segura(nova_senha)
        if not valido:
            messages.error(request, mensagem)
            return render(request, 'redefinir_senha.html', {'email': email, 'token': token})
        
        try:
            user = CustomUser.objects.get(email__iexact=email)
            
            user.set_password(nova_senha)
            user.save()

            cache.delete(f'email_verificado_{email}_{token}')
            cache.delete(f'codigo_recuperacao_{email}')
            cache.delete(f'token_recuperacao_{email}')

            logger.info(f'Senha redefinida com sucesso para {email}')
            messages.success(request, 'Senha redefinida com sucesso! Faça login com sua nova senha.')
            return redirect('login')
        
        except CustomUser.DoesNotExist:
            logger.error(f'Tentativa de redefinir senha para usuário inexistente: {email}')
            messages.error(request, 'Usuário não encontrado.')
            return redirect('esqueci_senha')
    
    return render(request, 'redefinir_senha.html', {'email': email, 'token': token})