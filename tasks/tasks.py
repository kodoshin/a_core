from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone


@shared_task
def send_subscription_confirmation_email(user_id, plan_name, end_date_iso, amount_total, currency):
    """
    Send a confirmation e-mail to the user when a new subscription has
    been successfully created.
    """
    User = get_user_model()

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return  # The user has been deleted – nothing to do

    # end_date is transferred as ISO string to keep the task signature simple
    try:
        end_date = timezone.datetime.fromisoformat(end_date_iso)
    except Exception:
        end_date = None

    context = {
        "user": user,
        "plan_name": plan_name,
        "end_date": end_date,
        "amount_total": amount_total,
        "currency": currency,
        "site_domain": getattr(settings, "DOMAIN", ""),
    }

    subject = f"Your Subscription « {plan_name} » is active"
    message = render_to_string("emails/subscription_confirmation.txt", context)
    html_message = render_to_string("emails/subscription_confirmation.html", context)

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
    )


@shared_task
def add(x, y):
    return x + y