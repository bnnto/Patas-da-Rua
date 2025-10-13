from django.db import models

# Create your models here.

class Pet (models.Model):
    SEXO_CHOICES = [
        ('M', 'Macho'),
        ('F', 'Fêmea'),
    ]

    CASTRADO_CHOICES = [
        ('True', 'Sim'),
        ('False', 'Não'),
    ]

    nome = models.CharField(max_length=100)
    especie = models.CharField(max_length=100)
    porte = models.CharField(max_length=100)
    raca = models.CharField(max_length=50)
    peso = models.FloatField()
    idade = models.PositiveIntegerField()
    sexo = models.CharField(max_length=1, choices=SEXO_CHOICES)
    obs = models.TextField()
    foto = models.ImageField(upload_to="fotosPet/", null=True, blank=True)
    status = models.CharField(max_length=100, default="disponivel")
    historico_saude = models.TextField()
    castrado = models.BooleanField()

    def __str__(self):
        return f"{self.nome} ({self.raca} - {self.get_sexo_display()} - {self.idade} anos)"