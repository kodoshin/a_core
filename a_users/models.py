from django.db import models
from django.contrib.auth.models import User
from django.templatetags.static import static
from a_projects.models import Project
from b_coding.models import ChatCategory
from b_planning.models import PlanningChatCategory
from b_insights.models import InsightChatCategory
from fernet_fields import EncryptedCharField
from django.utils import timezone
from management.models import Subscription, SubscriptionPlan, SubscriptionBonus
import requests
from datetime import datetime, timezone as dt_timezone
from dateutil import parser as date_parser




class Country(models.Model):
    name = models.CharField(max_length=50)
    phone_code = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return str(self.name)


class Region(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='provinces')
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, blank=True, null=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class Profile(models.Model):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('freelancer', 'Freelancer'),
        ('entrepreneur', 'Entrepreneur'),
        ('developer', 'Developer'),
        ('other', 'Other'),
    ]
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
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('internal_tester', 'Internal Tester'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='avatars/', null=True, blank=True)
    displayname = models.CharField(max_length=20, null=True, blank=True)
    info = models.TextField(null=True, blank=True)
    default_project = models.ForeignKey(Project, on_delete=models.SET_NULL, related_name='profiles_with_default_project', blank=True, null=True)
    default_insights_project = models.ForeignKey(Project, on_delete=models.SET_NULL, related_name='profiles_with_default_insights_project', blank=True, null=True)
    default_chat_category = models.ForeignKey(ChatCategory, on_delete=models.DO_NOTHING, related_name='profiles_with_default_chat_category', blank=True, null=True)
    default_insight_chat_category = models.ForeignKey(InsightChatCategory, on_delete=models.DO_NOTHING, related_name='profiles_with_default_insight_chat_category', blank=True, null=True)
    default_planning_chat_category = models.ForeignKey(PlanningChatCategory, on_delete=models.DO_NOTHING, related_name='profiles_with_default_planning_chat_category', blank=True, null=True)
    github_access_key = EncryptedCharField(max_length=200, null=True, blank=True) # FallbackEncryptedTextField(max_length=255, null=True, blank=True) # models.CharField(max_length=255, null=True, blank=True) #
    github_token_expiration = models.DateTimeField(null=True, blank=True)
    xp_points = models.IntegerField(default=0)
    available_credits = models.IntegerField(default=0)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='other')
    country = models.ForeignKey(Country, on_delete=models.DO_NOTHING, related_name='profiles_with_country', blank=True, null=True)
    region = models.ForeignKey(Region, on_delete=models.DO_NOTHING, related_name='profiles_with_province', blank=True, null=True)
    city = models.CharField(max_length=50, null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    accept_marketing_communication = models.BooleanField(default=False) #S'il accepts de recevoir les nouveautés marketing
    profile_is_filled = models.BooleanField(default=False)
    onboarding_is_done = models.BooleanField(default=False)
    has_claimed_credits = models.BooleanField(default=False)
    accept_data_usage_policy = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    marketing_channel = models.CharField(max_length=20, choices=MARKETING, default='other')
    timezone = models.CharField(max_length=50, blank=True, null=True, help_text="User timezone detected automatically.")
    gmt_offset = models.CharField(max_length=10, blank=True, null=True, help_text="Difference between GMT and user timezone (e.g., GMT+01:00).")
    daily_credit_claim_date = models.DateField(null=True, blank=True)
    allow_data_usage_for_anonymous_ai_training = models.BooleanField(
        default=False,
        verbose_name='Allow data usage for anonymous AI training'
    )

    def __str__(self):
        return str(self.user)

    @property
    def is_paid_user(self):
        """
        Retourne True si l'utilisateur est sur un plan payant (prix mensuel ou annuel > 0).
        """
        plan = self.current_plan
        return (plan.original_price or 0) > 0 or (plan.original_price or 0) > 0

    @property
    def current_subscription(self):
        now = timezone.now()
        return Subscription.objects.filter(
            user=self.user,
            active=True,
            start_date__lte=now,
            end_date__gte=now
        ).order_by('-start_date').first()

    @property
    def current_plan(self):
        subscription = self.current_subscription
        if subscription and subscription.plan:
            return subscription.plan
        # fallback vers le plan gratuit
        return SubscriptionPlan.get_default_free_plan()

    def _parse_github_expiration(self, value: str):
        """
        Convert the GitHub-Authentication-Token-Expiration header
        into a timezone-aware UTC datetime.
        """
        if not value:
            return None

        patterns = (
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S %Z",
            "%Y-%m-%d %H:%M:%S %z",
        )

        for fmt in patterns:
            try:
                dt = datetime.strptime(value, fmt)
                # if naïve, attach UTC
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=dt_timezone.utc)
                return dt.astimezone(dt_timezone.utc)
            except ValueError:
                continue

        # fallback to dateutil
        try:
            dt = date_parser.parse(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=dt_timezone.utc)
            return dt.astimezone(dt_timezone.utc)
        except Exception:
            return None

    def fetch_github_token_expiration(self):
        """
        Call GitHub, read the expiration header and persist it.
        """
        if not self.github_access_key:
            return None

        headers = {
            "Authorization": f"token {self.github_access_key}",
            "Accept": "application/vnd.github+json",
        }
        try:
            r = requests.get("https://api.github.com/user", headers=headers, timeout=5)
            exp_str = r.headers.get("GitHub-Authentication-Token-Expiration")
            exp_dt = self._parse_github_expiration(exp_str)
            if exp_dt:
                self.github_token_expiration = exp_dt
                self.save(update_fields=["github_token_expiration"])
                return exp_dt
        except requests.RequestException:
            pass
        return self.github_token_expiration

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


class CreditClaim(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='credit_claims')
    credits = models.PositiveIntegerField(default=20)
    claimed_at = models.DateTimeField(auto_now_add=True)
    subscription_bonus = models.ForeignKey(
        SubscriptionBonus,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='bonus_claims'
    )

    def __str__(self):
        base = f'{self.profile.user.username} claimed {self.credits} credits on {self.claimed_at}'
        if self.subscription_bonus:
            return f'{base} via coupon {self.subscription_bonus.code}'
        return base


class Policy (models.Model):
    name = models.CharField(max_length=50, null=True, blank=True)
    content = models.TextField()

    def __str__(self):
        return self.name

