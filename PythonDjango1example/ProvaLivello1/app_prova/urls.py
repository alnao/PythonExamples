from django.urls import path
from .views import chi_siamo,contatti

urlpatterns = [
    path('chi_siamo',chi_siamo,name="ChiSiamo"),
    path('contatti',contatti,name="Contatti")
]
