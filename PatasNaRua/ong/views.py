from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Pet
from rest_framework import status

def cadpet_page(request):
    return render(request, "cadpet.html")

def infopet_ong(request):
    return render(request, "infopet_ong.html")

def localpet_ong(request):
    return render(request, "localpet.html")

@api_view(["POST"])
def cadpet_view(request):
    nome = request.data.get("nome")
    especie = request.data.get("especie")
    porte = request.data.get("porte")
    raca = request.data.get("raca")
    peso = None
    idade = None
    sexo = request.data.get("sexo")
    obs = request.data.get("obs")
    foto = request.FILES.get("foto")
    historico_saude = request.data.get("historico_saude")

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

    if not nome or not especie or not porte or not raca or not sexo or not foto or peso is None or idade is None or not historico_saude:
        return Response(
            {"erro": "Faltam campos obrigatorios: Nome, Raca, Peso, Idade, Sexo e Foto."},
            status=status.HTTP_400_BAD_REQUEST
        )

    pet = Pet.objects.create(
        nome=nome,
        especie=especie,
        porte=porte,
        raca=raca,
        peso=peso,
        idade=idade,
        sexo=sexo,
        obs=obs,
        foto=foto,
        historico_saude = historico_saude
    )

    return Response({
        "status": "ok",
        "mensagem": "Pet cadastrado com sucesso",
        "dados": {
            "id": pet.id,
            "nome": pet.nome,
            "especie": pet.especie,
            "porte": pet.porte,
            "raca": pet.raca,
            "peso": pet.peso,
            "idade": pet.idade,
            "sexo": pet.sexo,
            "obs": pet.obs,
            "historico_saude": pet.historico_saude,
            "foto": pet.foto.url if pet.foto else None
        }
    })