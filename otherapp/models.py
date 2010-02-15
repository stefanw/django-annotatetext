from django.db import models

class ToBeAnnotated(models.Model):
    text = models.TextField()
    
    annotatable = True
    
    def get_absolute_url(self):
        return "/"
