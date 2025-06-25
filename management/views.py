from .models import SubscriptionPlan, CreditOffer, Subscription
from django.conf import settings
from decimal import Decimal
import stripe
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from a_users.models import Profile
from django.contrib.auth.models import User
from django.utils import timezone





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
    amount_multiplier = 100

    # ---------- 1. Calcul du crédit éventuel ----------
    if plan.is_yearly :
        previous_subscription = Subscription.objects.filter(
            user=request.user,
            active=True,
            end_date__gt=timezone.now()
        ).order_by('-start_date').first()
        credit_amount = Decimal('0')
        # Soustraire le montant restant de l'abonnement actuel
        if previous_subscription:
            credit_amount = previous_subscription.remaining_amount()
    else :
        previous_subscription = None
        credit_amount = 0

    # ---------- 2. Préparation du line_item ----------
    price_id = plan.stripe_plan_id
    success_url = f"{settings.DOMAIN}{reverse('pricing_credits')}?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{settings.DOMAIN}{reverse('pricing_credits')}"

    line_item = {'price': price_id, 'quantity': 1}

    # Utilisation d’un prix dynamique si : pas de price_id ou crédit à appliquer
    if credit_amount > 0 or not price_id:
        effective_price = max(Decimal(plan.current_price) - credit_amount, Decimal('0'))
        line_item = {
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': plan.name,
                    'tax_code': plan.stripe_tax_code or None,
                },
                'unit_amount': int(effective_price * amount_multiplier),
                'tax_behavior': 'exclusive',
            },
            'quantity': 1,
        }

    # ---------- 3. Remise via coupon si on conserve le price_id ----------
    discounts = []
    if credit_amount > 0 and price_id:
        coupon = stripe.Coupon.create(
            amount_off=int(credit_amount * amount_multiplier),
            currency='usd',
            duration='once'
        )
        discounts = [{'coupon': coupon.id}]

    # ---------- 4. Création de la session Checkout ----------
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[line_item],
        mode='payment',
        success_url=success_url,
        cancel_url=cancel_url,
        billing_address_collection='required',
        automatic_tax={'enabled': True},
        discounts=discounts,
        metadata={
            'plan_id': plan.id,
            'user_id': request.user.id,
            'previous_subscription_id': previous_subscription.id if previous_subscription else ''
        }
    )
    return redirect(session.url, code=303)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Réception des évènements Stripe."""
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        # Payload invalide ou signature incorrecte ⇒ 400.
        return HttpResponse(status=400)

    # Nous ne traitons ici que le checkout réussi.
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]

        # On récupère la session « complète » pour avoir total_details.
        session_full = stripe.checkout.Session.retrieve(
            session["id"], expand=["total_details"]
        )
        metadata = session_full.get("metadata", {}) or {}

        try:
            user = User.objects.get(id=metadata.get("user_id"))
        except User.DoesNotExist:
            # Pas d’utilisateur ⇒ on arrête, mais on renvoie 200 à Stripe.
            return HttpResponse(status=200)

        # ---------- 1. Désactivation de l’ancien abonnement ----------
        previous_subscription_id = metadata.get("previous_subscription_id")
        if previous_subscription_id:
            try:
                old_sub = Subscription.objects.get(id=previous_subscription_id)
                if old_sub.active:
                    old_sub.active = False
                    old_sub.end_date = timezone.now()
                    old_sub.save()
            except Subscription.DoesNotExist:
                pass  # Rien à désactiver

        # ---------- 2. Création du nouvel abonnement ----------
        plan = get_object_or_404(SubscriptionPlan, id=metadata.get("plan_id"))

        Subscription.objects.create(
            user=user,
            plan=plan,
            amount_subtotal=Decimal(session_full.amount_subtotal or 0) / 100,
            tax_amount=Decimal(
                (session_full.total_details.amount_tax or 0)
            ) / 100,
            amount_total=Decimal(session_full.amount_total or 0) / 100,
            currency=(session_full.currency or "usd").upper(),
        )

    # Toujours renvoyer 200 pour indiquer à Stripe que l’évènement est géré.
    return HttpResponse(status=200)

