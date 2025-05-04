from .models import SubscriptionPlan, CreditOffer
from django.conf import settings

import stripe
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from a_users.models import Profile




def pricing_credits(request):
    subscription_plans = SubscriptionPlan.objects.all()
    credit_offers = CreditOffer.objects.all()
    context = {
        'subscription_plans': subscription_plans,
        'credit_offers': credit_offers,
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY
    }
    return render(request, 'management/pricing_credits.html', context)



stripe.api_key = settings.STRIPE_SECRET_KEY

@require_POST
def create_checkout_session(request, offer_id):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    offer = get_object_or_404(CreditOffer, id=offer_id)
    success_url = f"{settings.DOMAIN}{reverse('pricing_credits')}?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{settings.DOMAIN}{reverse('pricing_credits')}"
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {'name': f"{offer.name} Credits"},
                'unit_amount': int(offer.price * 100),
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=success_url,
        cancel_url=cancel_url,
    )
    return redirect(session.url, code=303)

@require_POST
def create_checkout_session_plan(request, plan_id):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    offer = get_object_or_404(SubscriptionPlan, id=plan_id)
    success_url = f"{settings.DOMAIN}{reverse('pricing_credits')}?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{settings.DOMAIN}{reverse('pricing_credits')}"
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {'name': f"{offer.name}"},
                'unit_amount': int(offer.yearly_price * 100),
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=success_url,
        cancel_url=cancel_url,
    )
    return redirect(session.url, code=303)



@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        offer_id = session['metadata']['offer_id']
        user_id = session['metadata']['user_id']
        offer = CreditOffer.objects.get(id=offer_id)
        profile = Profile.objects.get(user_id=user_id)
        profile.available_credits += offer.credits
        profile.save()

    return HttpResponse(status=200)