from django.db import models

# Create your models here.

class Pet (models.Model):
    SEXO_CHOICES = [
        ('M', 'Macho'),
        ('F', 'Fêmea'),
    ]

    nome = models.CharField(max_length=100)
    raca = models.CharField(max_length=50)
    peso = models.FloatField()
    idade = models.PositiveIntegerField()
    sexo = models.CharField(max_length=1, choices=SEXO_CHOICES)
    obs = models.TextField()
    foto = models.ImageField(upload_to="fotosPet/", null=True, blank=True)

    def __str__(self):
        return f"{self.nome} ({self.raca} - {self.get_sexo_display()} - {self.idade} anos)"