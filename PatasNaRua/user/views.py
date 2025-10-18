from django.shortcuts import render, get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from ong.models import Pet

def tela_user_page(request):
    return render(request, "tela_user.html")

def detalhes_pet(request, pet_id):
    pet = get_object_or_404(Pet, id=pet_id)
    return render(request, "detalhes_pet.html", {"pet": pet})
