from django.db import models
from django.urls import reverse
# campi modello nella documentazione
# fields https://docs.djangoproject.com/en/3.1/ref/models/fields/
class Giornalista(models.Model): #tra parentesi = extends
    nome=models.CharField(max_length=42) #vedere documentazione per parametri
    cognome=models.CharField(max_length=42)
    def __str__(self):
        return self.nome + " " + self.cognome
    class Meta:
        verbose_name:"Giornalista"
        verbose_name_plural="Giornalisti"

class Articolo(models.Model):
    titolo = models.CharField(max_length=42)
    testo = models.TextField()
    scrittore = models.ForeignKey('Giornalista',on_delete=models.CASCADE,related_name="articoli")#chiave esterna relazione uno a molti, related è inversa
    def __str__(self):
        return self.titolo
    def get_absolute_url(self):
        return reverse("dettaglio_articolo",kwargs={"pk":self.pk})
    class Meta:
        verbose_name:"Articolo"
        verbose_name_plural="Articoli"
