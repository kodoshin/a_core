from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

User = get_user_model()

@receiver(post_save, sender=User, dispatch_uid="send_welcome_email_to_new_user")
def send_welcome_email(sender, instance, created, **kwargs):
    """
    Envoie un e-mail de bienvenue dès qu’un nouvel utilisateur est enregistré.
    """
    if created and instance.email:
        subject = "Bienvenue sur Kodoshin"
        message = (
            f"Welcome {instance.username},\n\n"
            "Welcome to Kodoshin !\n"
            "We're happy to have you as a new member.\n\n"
            "— Kodoshin Team"
        )
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[instance.email],
            fail_silently=True,
        )