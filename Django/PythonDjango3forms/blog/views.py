from django.shortcuts import render
from .forms import BlogPostModelForm
from django.http import HttpResponse
def crea_post_view(request):
    if request.method=="POST":
        form=BlogPostModelForm(request.POST)
        if form.is_valid():
            print("Form valido con titolo="+form.cleaned_data["titolo"])
            new_post=form.save() #salvataggio
            print(new_post)
            return HttpResponse("<h1>Post creato con successo</h1>");
    else:
        form=BlogPostModelForm()
    return render( request, "crea.html",context={"form":form})
