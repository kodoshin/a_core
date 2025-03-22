from django.db import models
from django.contrib.auth.models import User


class GitHubAccount(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    github_id = models.IntegerField()
    access_token = models.TextField(blank=True, null=True)


class AllowedFile(models.Model):
    name = models.CharField(max_length=20, blank=True, null=True)
    extension = models.CharField(max_length=20)
    description = models.CharField(max_length=50, blank=True, null=True)

