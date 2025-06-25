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


import logging
logger = logging.getLogger(__name__)
@csrf_exempt
def stripe_webhook(request):
    """
    Réception des évènements Stripe.
    Seul checkout.session.completed est géré actuellement.
    La fonction DOIT toujours retourner un 2xx à Stripe lorsqu’elle a
    correctement traité (ou ignoré) l’évènement, afin d’éviter des retries.
    """

    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

    # 1. Vérification de la signature -------------------------------------------------
    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=settings.STRIPE_WEBHOOK_SECRET,
        )
    except ValueError:
        logger.exception("Stripe webhook ‑ payload invalide")
        return HttpResponse("Invalid payload", status=400)
    except stripe.error.SignatureVerificationError:
        logger.exception("Stripe webhook ‑ signature invalide")
        return HttpResponse("Invalid signature", status=400)

    # 2. Traitement de checkout.session.completed -------------------------------------
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        metadata = session.get("metadata", {}) or {}

        # --- Récupération de l’utilisateur -------------------------------------------
        try:
            user = User.objects.get(pk=int(metadata.get("user_id", 0)))
            logger.info("USER FOUND: %s", user)
        except (User.DoesNotExist, ValueError):
            logger.error("Stripe webhook ‑ user introuvable dans la metadata : %s", metadata)
            return HttpResponse(status=200)     # On stoppe mais on confirme à Stripe

        # --- Désactivation de l’abonnement précédent --------------------------------
        try:
            previous_subscription = (
                Subscription.objects.filter(user=user, active=True)
                .order_by("-start_date")
                .first()
            )
        except :
            previous_subscription = None
        if previous_subscription:
            previous_subscription.active = False
            previous_subscription.end_date = timezone.now()
            previous_subscription.save(update_fields=["active", "end_date"])

        # --- Création du nouvel abonnement ------------------------------------------
        plan_id = metadata.get("plan_id")
        if plan_id:
            try:
                plan = SubscriptionPlan.objects.get(pk=int(plan_id))
                """
                Subscription.objects.create(
                    user=user,
                    plan=plan,
                    amount_subtotal=Decimal(session["amount_subtotal"]) / 100,
                    tax_amount=Decimal(session["total_details"]["amount_tax"] or 0) / 100,
                    amount_total=Decimal(session["amount_total"]) / 100,
                    currency=session["currency"].upper(),
                )
                """
            except SubscriptionPlan.DoesNotExist:
                logger.error("Stripe webhook ‑ plan %s inexistant", plan_id)

    # 3. Réponse ----------------------------------------------------------------------
    return HttpResponse(status=200)
