from django.test import TestCase
from django.urls import resolve,reverse
from news_app.views import home
from news_app.models import Giornalista

#test sulla vista home
class HomeViewTest(TestCase):
    #all'url c'è quel metodo
    def test_url_resolves_home_view(self):
        view=resolve("/home/")
        self.assertEqual(view.func,home)#confronta le funzioni al url
    #l'url risponde con 200 e non altri errori strani
    def test_url_resolve_home_name(self):
        url=reverse("HomeView")
        response = self.client.get(url)
        self.assertEquals(response.status_code,200)
class GiornalistaTestCAse(TestCase):
    #qui si stesta il tostring di un elemento dopo averlo in inserito nella base dati
    def setUp(self):
        Giornalista.objects.create(nome="Giudo",cognome="Ross")
    def testGiornalistaStr(self):
        g=Giornalista.objects.get(nome="Giudo")
        self.assertEqual(g.__str__(), "Giudo Ross")
