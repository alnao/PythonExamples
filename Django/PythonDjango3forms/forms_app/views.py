from django.shortcuts import render
from .forms import ContattoForm
from django.http import HttpResponse
def home(request):
    return render(request,"home.html")
def contatto(request):
    if request.method == "POST":
        form = ContattoForm(request.POST)
        if form.is_valid():
            print("Form Valido")
            print("nome:" + form.cleaned_data["nome"])
            print("cognome:" + form.cleaned_data["cognome"])
            return HttpResponse("<h1>Grazie </h1>")
    else:
        form = ContattoForm()
    return render(request,"contatto.html",context={"form":form})
