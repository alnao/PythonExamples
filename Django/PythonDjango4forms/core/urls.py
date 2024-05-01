from django.urls import path
from . import views
urlpatterns = [
    path('', views.homepage,name="homepage"),
    path('user/<str:username>', views.user_profile_view,name="user_profile"),
    path('user_list', views.UserList.as_view(),name="user_list"),
]
