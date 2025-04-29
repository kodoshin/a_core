from django.db import models
from datetime import timedelta
from django.contrib.auth.models import User


class AIModel(models.Model):
    PROVIDER_CHOICES = [
        ('openai', 'OpenAI'),
        ('claude', 'Claude AI'),
        ('gemini', 'Google Gemini'),
        ('other', 'Other'),
    ]

    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    name = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.get_provider_display()} - {self.name}"


class APIKey(models.Model):
    ai_model = models.ForeignKey(AIModel, on_delete=models.CASCADE, null=True)
    api_key = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.ai_model.name} - {self.api_key[:5]}"


class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=100)
    monthly_price = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    yearly_price = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    original_monthly_price = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    original_yearly_price = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    monthly_credits = models.PositiveIntegerField(default=0)
    daily_credits = models.PositiveIntegerField(default=0)
    project_limits = models.PositiveIntegerField(default=0)
    sync_with_github = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    advantages = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name


class Subscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.end_date:
            self.end_date = self.start_date + timedelta(days=self.plan.duration_days)
        super().save(*args, **kwargs)


class CreditOffer(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    original_price = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    credits = models.IntegerField()
    original_credits = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class DiscountCoupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount_percentage = models.FloatField()
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    active = models.BooleanField(default=True)

    def is_valid(self):
        now = timezone.now()
        return self.active and self.valid_from <= now <= self.valid_until

