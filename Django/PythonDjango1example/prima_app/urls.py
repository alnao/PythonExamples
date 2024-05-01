from django.urls import path
from prima_app import views as prima_app_views
urlpatterns = [
	path('homepage',prima_app_views.homepage,name='Home')
]
