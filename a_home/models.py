from django.db import models
from cloudinary.models import CloudinaryField



class Persona(models.Model):
    STATUS_CHOICES = [
        ('active', 'active'),
        ('inactive', 'inactive'),
        ('coming_soon', 'coming soon'),
    ]
    #image = models.ImageField(upload_to='personas/')
    image = CloudinaryField('image', blank=True, null=True)
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255)
    slug = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.title


class AiToolEvaluation(models.Model):
    ai_tool = models.CharField(max_length=50)
    code_personalization = models.PositiveSmallIntegerField(default=0)
    github_integration = models.PositiveSmallIntegerField(default=0)
    context_understanding = models.PositiveSmallIntegerField(default=0)
    suggestion_accuracy = models.PositiveSmallIntegerField(default=0)
    development_speed = models.PositiveSmallIntegerField(default=0)
    explanation_effort = models.PositiveSmallIntegerField(default=0)
    user_experience = models.PositiveSmallIntegerField(default=0)

    def __str__(self):
        return self.ai_tool