from django import forms
from django.core import validators
from django.core.exceptions import ValidationError
class ContattoForm(forms.Form):
    nome=forms.CharField(max_length=25,widget=forms.TextInput(attrs={"class":"form-control"}))
    cognome=forms.CharField(max_length=25,widget=forms.TextInput(attrs={"class":"form-control"}))
    email=forms.EmailField(max_length=255,widget=forms.TextInput(attrs={"class":"form-control"}))
    contenuto=forms.CharField(widget=forms.Textarea(attrs={"class":"form-control","placeholder":"Inserisci il messaggio"}),validators=[validators.MinLengthValidator(10)])
    def clean_contenuto(self): 
        dati=self.cleaned_data["contenuto"]
        if "vietata" in dati:
            raise ValidationError("Nel contenuto la parola vietata")
        return dati
