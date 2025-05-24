from django.db import models
from datetime import timedelta
from django.contrib.auth.models import User
from django.db.models import Q
from django.db.models import F
from django.utils import timezone


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
    KEY_TYPE_CHOICES = [
        ('chat', 'Chat'),
        ('chat-large', 'Chat Large'),
        ('chat-ultimate', 'Chat Ultimate'),
        ('title', 'Title'),
        ('ai1', 'AI1'),
        ('ai2', 'AI2'),
        ('documentation', 'Documentation'),
        ('other', 'Other'),
    ]
    ai_model = models.ForeignKey(AIModel, on_delete=models.CASCADE, null=True)
    key_type = models.CharField(max_length=20, choices=KEY_TYPE_CHOICES, default='chat')
    api_key = models.CharField(max_length=255)
    real_time_users = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.ai_model.name} ({self.key_type}) - users: {self.real_time_users}'

    def increment(self):
        APIKey.objects.filter(pk=self.pk).update(real_time_users=F('real_time_users') + 1)

    def decrement(self):
        APIKey.objects.filter(pk=self.pk).update(real_time_users=F('real_time_users') - 1)


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
    duration_days = models.PositiveIntegerField(default=366)
    regeneration_attempts = models.PositiveIntegerField(default=0)
    large_models = models.BooleanField(default=False)
    advanced_models = models.BooleanField(default=False)

    stripe_tax_code = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text='Stripe Tax Code for automatic_tax (e.g., txcd_56151200 for digital services)'
    )

    def __str__(self):
        return self.name

    @classmethod
    def get_default_free_plan(cls):
        """
        Retourne le plan dont le prix est égal à zéro (plan gratuit).
        """
        return cls.objects.filter(
            Q(monthly_price=0) | Q(yearly_price=0)
        ).order_by('created_at').first()


class Subscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    active = models.BooleanField(default=True)

    amount_subtotal = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    amount_total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, null=True, blank=True)

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
    #bonus_credits = models.IntegerField(default=0)  # Crédit bonus offert
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    active = models.BooleanField(default=True)

    def is_valid(self):
        now = timezone.now()
        return self.active and self.valid_from <= now <= self.valid_until

    def __str__(self):
        return self.code


class SubscriptionBonus(models.Model):
    code = models.CharField(max_length=50, unique=True)
    credits = models.PositiveIntegerField(default=0)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    active = models.BooleanField(default=True)

    def is_valid(self):
        now = timezone.now()
        return self.active and self.valid_from <= now <= self.valid_until

    def __str__(self):
        return f"{self.code} ({self.credits} crédits)"

