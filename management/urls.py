from django.urls import path
from .views import pricing_credits, create_checkout_session, create_checkout_session_plan, stripe_webhook

urlpatterns = [
    path('', pricing_credits, name='pricing_credits'),

    path('create-checkout-session/<int:offer_id>/', create_checkout_session, name='create_checkout_session'),
    path('create-plan-checkout-session/<int:plan_id>/', create_checkout_session_plan, name='create_checkout_session_plan'),
    path('stripe/webhook/', stripe_webhook, name='stripe_webhook'),
]
