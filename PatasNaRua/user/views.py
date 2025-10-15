from django.shortcuts import render

from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

def tela_user_page(request):
    return render(request, "tela_user.html")
# Create your views here.
