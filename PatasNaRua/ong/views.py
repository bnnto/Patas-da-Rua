from django.shortcuts import render, get_object_or_404, redirect
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
    info = request.data.get("info")
    foto = request.FILES.get("foto")
    historico_saude = request.data.get("historico_saude")
    castrado = request.data.get("castrado")

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

    if not all([nome, especie, porte, raca, sexo, castrado, foto]) or peso is None or idade is None:
        return Response(
            {"erro": "Preencha todos os campos obrigatórios: Nome, Espécie, Porte, Raça, Peso, Idade, Sexo, Castrado e Foto."},
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
        info=info,
        foto=foto,
        historico_saude = historico_saude,
        castrado=castrado
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
            "info": pet.info,
            "historico_saude": pet.historico_saude,
            "foto": pet.foto.url if pet.foto else None
        }
    })

def editar_pet(request, pet_id):
    pet = get_object_or_404(Pet, id=pet_id)

    if request.method == "POST":
        pet.nome = request.POST.get('nome')
        pet.especie = request.POST.get('especie')
        pet.porte = request.POST.get('porte')
        pet.raca = request.POST.get('raca')
        pet.peso = request.POST.get('peso')
        pet.idade = request.POST.get('idade')
        pet.sexo = request.POST.get('sexo')
        pet.info = request.POST.get('info')
        pet.historico_saude = request.POST.get('historico_saude')
        
        if 'foto' in request.FILES:
            pet.foto = request.FILES['foto']

        pet.save()
        return redirect('detalhes_pet', pet_id=pet.id)

    return render(request, 'editar_pet.html', {'pet': pet})