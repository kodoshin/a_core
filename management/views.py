from django.shortcuts import render
from .models import SubscriptionPlan, CreditOffer
from django.conf import settings

import stripe
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
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

def create_checkout_session(request, offer_id):
    offer = get_object_or_404(CreditOffer, id=offer_id)
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': f'{offer.name} Credits',
                },
                'unit_amount': int(offer.price * 100),
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=request.build_absolute_uri('/management/pricing_credits/') + '?session_id={CHECKOUT_SESSION_ID}',
        cancel_url=request.build_absolute_uri('/management/pricing_credits/'),
        metadata={
            'offer_id': str(offer.id),
            'user_id': str(request.user.id),
        }
    )
    return JsonResponse({'sessionId': session.id})

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