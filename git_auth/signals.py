from allauth.socialaccount.models import SocialAccount
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from a_users.models import Profile
from b_coding.models import ChatCategory


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        default_chat_category = ChatCategory.objects.filter(type='regular').first()
        social_account = SocialAccount.objects.filter(user=instance, provider="github").first()
        displayname = social_account.extra_data.get("login") if social_account else instance.username
        Profile.objects.create(
            user=instance,
            default_chat_category=default_chat_category,
            displayname=displayname,
            available_credits=500,
        )
