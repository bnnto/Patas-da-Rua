from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Pet
from rest_framework import status

def cadpet_page(request):
    return render(request, "cadpet.html")

# Create your views here.
@api_view(["POST"])
def cadpet_view(request):
    nome = request.data.get("nome")
    raca = request.data.get("raca")
    peso = None
    idade = None
    sexo = request.data.get("sexo")
    obs = request.data.get("obs")
    foto = request.FILES.get("foto")

    try:
        peso_str = request.data.get("peso")
        idade_str = request.data.get("idade")

        if peso_str:
            peso = float(peso_str.strip().replace(',', '.')) 

        if idade_str:
            idade = int(idade_str.strip())

    except ValueError:
        return Response(
            {"erro": "Os campos peso e idade devem ser numeros."},
            status=status.HTTP_400_BAD_REQUEST
    )

#    if not nome or not raca or not sexo or not foto or peso is None or idade is None:
#        return Response(
#            {"erro": "Faltam campos obrigatorios: Nome, Raca, Peso, Idade, Sexo e Foto."},
#            status=status.HTTP_400_BAD_REQUEST
#        )

    pet = Pet.objects.create(
        nome=nome,
        raca=raca,
        peso=peso,
        idade=idade,
        sexo=sexo,
        obs=obs,
        foto=foto
    )

    return Response({
        "status": "ok",
        "mensagem": "Pet cadastrado com sucesso",
        "dados": {
            "id": pet.id,
            "nome": pet.nome,
            "raca": pet.raca,
            "peso": pet.peso,
            "idade": pet.idade,
            "sexo": pet.sexo,
            "obs": pet.obs,
            "foto": pet.foto.url if pet.foto else None
        }
    })