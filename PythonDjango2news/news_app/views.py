from django.shortcuts import render,get_object_or_404
from django.http import HttpResponse
from .models import Articolo,Giornalista
def home(request):
    articoli=Articolo.objects.all()
    giornalisti=Giornalista.objects.all()
    context={"articoli":articoli,"giornalisti":giornalisti}
    return render (request,"homepage.html",context)

def dettaglioArticolo(request,idArticolo):
    articolo=get_object_or_404(Articolo,pk=idArticolo)
    context={"articolo":articolo}
    return render (request,"articolo.html",context)

# Classe based views https://docs.djangoproject.com/en/3.1/ref/class-based-views/generic-display/
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
class ArticoloDetailView(DetailView):
    model=Articolo
    template_name="articolo.html"

class ArticoliListView(ListView):
    model = Articolo
    template_name = "articoli.html"
