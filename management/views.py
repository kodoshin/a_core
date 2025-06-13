from .models import SubscriptionPlan, CreditOffer, Subscription
from django.conf import settings

import stripe
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from a_users.models import Profile
from django.contrib.auth.models import User





def pricing_credits(request):
    monthly_plans = SubscriptionPlan.objects.filter(is_yearly=False).order_by('original_price')
    yearly_plans = SubscriptionPlan.objects.filter(is_yearly=True).order_by('original_price')
    credit_offers = CreditOffer.objects.order_by('original_price')
    context = {
        'monthly_plans': monthly_plans,
        'yearly_plans':  yearly_plans,
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
        billing_address_collection='auto',
        automatic_tax={'enabled': True},
        metadata={
            'offer_id': offer.id,
            'user_id': request.user.id
        }
    )
    return redirect(session.url, code=303)

@require_POST
def create_checkout_session_plan(request, plan_id):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    plan = get_object_or_404(SubscriptionPlan, id=plan_id)
    price_id = plan.stripe_plan_id
    success_url = f"{settings.DOMAIN}{reverse('pricing_credits')}?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{settings.DOMAIN}{reverse('pricing_credits')}"
    line_item = {
        'price_data': {
            'currency': 'usd',
            'product_data': {
                'name': plan.name,
                # use plan-specific tax code or fallback to digital services code
                'tax_code': plan.stripe_tax_code or None,
            },
            'unit_amount': int(plan.current_price * 100),
            'tax_behavior': 'exclusive',
        },
        'quantity': 1,
    }
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[line_item],
        mode='payment',
        success_url=success_url,
        cancel_url=cancel_url,
        billing_address_collection='required',
        automatic_tax={'enabled': True},
        metadata={'plan_id': plan.id, 'user_id': request.user.id}
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
        # Retrieve expanded session to get total_details
        session_full = stripe.checkout.Session.retrieve(
            session['id'],
            expand=['total_details']
        )
        metadata = session_full.get('metadata', {})
        user = User.objects.get(id=metadata.get('user_id'))
        if 'plan_id' in metadata:
            plan = SubscriptionPlan.objects.get(id=metadata['plan_id'])
            Subscription.objects.create(
                user=user,
                plan=plan,
                amount_subtotal=session_full.amount_subtotal / 100,
                tax_amount=(session_full.total_details.amount_tax or 0) / 100,
                amount_total=session_full.amount_total / 100,
                currency=session_full.currency.upper()
            )
    return HttpResponse(status=200)