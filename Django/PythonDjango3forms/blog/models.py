from django.db import models
class BlogPostModel(models.Model):
    titolo=models.CharField(max_length=50)
    contenuto=models.TextField()
    bozza=models.BooleanField()
    def __str__(self):
        return self.titolo
