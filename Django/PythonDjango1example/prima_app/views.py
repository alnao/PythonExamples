from django.shortcuts import render #gia c'era
from django.http import HttpResponse

def homepage(request):
    return HttpResponse("<h1>risposta prima_app</h1>")
