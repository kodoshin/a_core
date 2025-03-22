from django.db import models


class Persona(models.Model):
    STATUS_CHOICES = [
        ('active', 'active'),
        ('coming_soon', 'coming soon'),
    ]
    image = models.ImageField(upload_to='personas/')
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255)
    slug = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )

    def __str__(self):
        return self.title


class AiToolEvaluation(models.Model):
    ai_tool = models.CharField(max_length=50)
    code_personalization = models.PositiveSmallIntegerField(default=0)
    github_integration = models.PositiveSmallIntegerField(default=0)
    context_understanding = models.PositiveSmallIntegerField(default=0)
    suggestion_accuracy = models.PositiveSmallIntegerField(default=0)
    development_speed = models.PositiveSmallIntegerField(default=0)
    effort_explanation = models.PositiveSmallIntegerField(default=0)
    user_experience = models.PositiveSmallIntegerField(default=0)

    def __str__(self):
        return self.ai_tool