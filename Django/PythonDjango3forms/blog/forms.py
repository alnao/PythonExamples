from django.forms import ModelForm
from .models import BlogPostModel
class BlogPostModelForm(ModelForm):
    class Meta:
        model = BlogPostModel
        fields = "__all__"
