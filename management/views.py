from django.shortcuts import render
from .models import SubscriptionPlan, CreditOffer




def pricing_credits(request):
    subscription_plans = SubscriptionPlan.objects.all()
    credit_offers = CreditOffer.objects.all()
    context = {
        'subscription_plans': subscription_plans,
        'credit_offers': credit_offers
    }
    return render(request, 'management/pricing_credits.html', context)