from django.contrib.auth.models import AbstractUser
from phonenumber_field.modelfields import PhoneNumberField
from django.db import models

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)

    telefone = PhoneNumberField(region='BR', blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email
    
    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"

class UsuarioComum(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='usuario_comum')
    cpf = models.CharField(max_length=14, unique=True)
    data_nascimento = models.DateField()
    endereco = models.TextField()

    def __str__(self):
        return self.user.get_full_name() or self.user.email
    
    class Meta:
        verbose_name = "Usuário Comum"
        verbose_name_plural = "Usuários Comuns"

class ONG(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='ong')
    nome_ong = models.CharField(max_length=200)
    cnpj = models.CharField(max_length=18, unique=True)
    endereco = models.TextField()
    email_institucional = models.EmailField(unique=True)
    nome_responsavel = models.CharField(max_length=200)
    cpf_responsavel = models.CharField(max_length=14)

    def __str__(self):
        return self.nome_ong
    
    class Meta:
        verbose_name = "ONG"
        verbose_name_plural = "ONGs"