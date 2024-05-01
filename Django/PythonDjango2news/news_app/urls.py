from django.contrib import admin
from django.urls import include, path
from news_app.views import  home,dettaglioArticolo,ArticoloDetailView,ArticoliListView
urlpatterns = [
    path('home/', home,name="HomeView"),
    #path('articolo/<int:idArticolo>', dettaglioArticolo,name="dettaglio_articolo"),
    path('articoli/', ArticoliListView.as_view(),name="articoli"),
    path('articolo/<int:pk>', ArticoloDetailView.as_view(),name="dettaglio_articolo"),
]
