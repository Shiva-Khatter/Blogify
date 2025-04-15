#Models.py
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.urls import reverse

class Post(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField()
    date_posted = models.DateTimeField(default=timezone.now)
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    seo_keywords = models.CharField(max_length=200, blank=True, null=True)
    is_draft = models.BooleanField(default=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('post-detail', kwargs={'pk': self.pk})
    
class ScheduledPost(models.Model):
    topic = models.CharField(max_length=200)
    primary_keyword = models.CharField(max_length=100)
    additional_keywords = models.CharField(max_length=500)  # Comma-separated
    scheduled_datetime = models.DateTimeField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.topic} - {self.scheduled_datetime}"