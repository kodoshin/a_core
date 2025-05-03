from django.urls import path
from .views import pricing_credits, create_checkout_session, stripe_webhook

urlpatterns = [
    path('', pricing_credits, name='pricing_credits'),

    path('create-checkout-session/<int:offer_id>/', create_checkout_session, name='create_checkout_session'),
    path('stripe/webhook/', stripe_webhook, name='stripe_webhook'),
]
