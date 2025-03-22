from django.db import models
from django.contrib.auth.models import User
from django.templatetags.static import static
from a_projects.models import Project
from b_coding.models import ChatCategory


class Country(models.Model):
    name = models.CharField(max_length=50)
    phone_code = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        ordering = ['name']
    def __str__(self):
        return str(self.name)


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='avatars/', null=True, blank=True)
    displayname = models.CharField(max_length=20, null=True, blank=True)
    info = models.TextField(null=True, blank=True)
    default_project = models.ForeignKey(Project, on_delete=models.DO_NOTHING, related_name='profiles_with_default_project', blank=True, null=True)
    default_chat_category = models.ForeignKey(ChatCategory, on_delete=models.DO_NOTHING, related_name='profiles_with_default_chat_category', blank=True, null=True)
    github_access_key = models.CharField(max_length=255, null=True, blank=True)
    xp_points = models.IntegerField(default=0)
    available_credits = models.IntegerField(default=0)
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('freelancer', 'Freelancer'),
        ('entrepreneur', 'Entrepreneur'),
        ('developer', 'Developer'),
        ('other', 'Other'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='other')
    country = models.ForeignKey(Country, on_delete=models.DO_NOTHING, related_name='profiles_with_country', blank=True, null=True)
    city = models.CharField(max_length=50, null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    accept_marketing_communication = models.BooleanField(default=False) #S'il accepts de recevoir les nouveautés marketing
    profile_is_filled = models.BooleanField(default=False)
    has_claimed_credits = models.BooleanField(default=False)
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('internal_tester', 'Internal Tester'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    MARKETING = [
        ('search engine', 'Search Engine'),
        ('linkedin', 'Linkedin'),
        ('X', 'X'),
        ('youtube', 'Youtube'),
        ('reddit', 'Reddit'),
        ('hacker news', 'Hacker News'),
        ('reference', 'Reference'),
        ('other', 'Other'),
    ]
    marketing_channel = models.CharField(max_length=20, choices=MARKETING, default='other')
    timezone = models.CharField(max_length=50, blank=True, null=True, help_text="User timezone detected automatically.")
    gmt_offset = models.CharField(max_length=10, blank=True, null=True, help_text="Difference between GMT and user timezone (e.g., GMT+01:00).")

    def __str__(self):
        return str(self.user)

    @property
    def name(self):
        if self.displayname:
            return self.displayname
        return self.user.username

    @property
    def avatar(self):
        if self.image:
            return self.image.url
        return static("images/avatar.svg")



