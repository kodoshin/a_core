from django.contrib import admin
from .models import APIKey, SubscriptionPlan, Subscription, DiscountCoupon, AIModel, CreditOffer, SubscriptionBonus



@admin.register(SubscriptionBonus)
class SubscriptionBonusAdmin(admin.ModelAdmin):
    list_display = ('code', 'credits', 'valid_from', 'valid_until', 'active')

@admin.register(AIModel)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ('provider', 'name')

@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ('ai_model', 'key_type', 'real_time_users', 'is_active', 'created_at')
    list_filter = ('key_type', 'is_active', 'ai_model__provider')

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'current_price', 'original_price', 'is_yearly')

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'start_date', 'end_date', 'active')

@admin.register(DiscountCoupon)
class DiscountCouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_percentage', 'valid_until', 'active')

@admin.register(CreditOffer)
class CreditOfferAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'credits')