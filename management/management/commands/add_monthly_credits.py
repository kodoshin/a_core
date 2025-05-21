from django.core.management.base import BaseCommand
from django.db.models import F
from django.utils import timezone
from management.models import Subscription


class Command(BaseCommand):
    help = 'Adds monthly credits to users with active subscriptions on their billing day.'

    def handle(self, *args, **options):
        today = timezone.localdate()
        subscriptions = Subscription.objects.filter(
            active=True
        ).select_related('plan', 'user__profile')
        for subscription in subscriptions:
            plan = subscription.plan
            if plan.monthly_credits > 0 and subscription.start_date.day == today.day:
                profile = subscription.user.profile
                profile.available_credits = F('available_credits') + plan.monthly_credits
                profile.save(update_fields=['available_credits'])
                self.stdout.write(self.style.SUCCESS(
                    f'Added {plan.monthly_credits} credits to {subscription.user.username}'
                ))