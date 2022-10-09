from django.shortcuts import render,get_object_or_404
from django.contrib.auth.models import User
from django.views.generic.list import ListView
# Create your views here.
def homepage(request):
    return render(request,'homepage.html')

def user_profile_view(request,username):
    user = get_object_or_404(User,username=username)
    context = {"user":user}
    return render(request,"user_profile.html",context)

class UserList(ListView):
    model=User
    template_name="user_list.html"
