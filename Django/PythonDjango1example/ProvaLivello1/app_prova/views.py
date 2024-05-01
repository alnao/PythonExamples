from django.shortcuts import render
from django.http import HttpResponse

def homepage(request):
    return HttpResponse("<h1>homepage prova livello1</h1>")

def chi_siamo(request):
    return HttpResponse("<h2>Chi siamo?</h2>")

def contatti(request):
    return HttpResponse("<h3>Mandami una mail</h3>")
