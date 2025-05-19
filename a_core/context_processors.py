

import pytz
from django.utils import timezone


def reset_daily_credits(request):
    if not request.user.is_superuser and request.user.is_authenticated:
        profile = request.user.profile
        try:
            user_tz = pytz.timezone(profile.timezone) if profile.timezone else timezone.get_current_timezone()
        except Exception:
            user_tz = timezone.get_current_timezone()

        local_today = timezone.now().astimezone(user_tz).date()

        # If the last claim date is not today and credits were already claimed, reset the flag
        if profile.daily_credit_claim_date != local_today and profile.has_claimed_credits:
            profile.has_claimed_credits = False
            try:
                profile.save()
            except:
                pass
    return {}

"""

import pytz
from django.utils import timezone
from asgiref.sync import sync_to_async

async def reset_daily_credits(request):
    if not request.user.is_superuser and request.user.is_authenticated:
        # Load the profile asynchronously to avoid sync DB access in async context
        profile = await sync_to_async(lambda: request.user.profile)()
        try:
            user_tz = pytz.timezone(profile.timezone) if profile.timezone else timezone.get_current_timezone()
        except Exception:
            user_tz = timezone.get_current_timezone()
        local_today = timezone.now().astimezone(user_tz).date()
        if profile.daily_credit_claim_date != local_today and profile.has_claimed_credits:
            profile.has_claimed_credits = False
            # Save the profile asynchronously
            await sync_to_async(profile.save)()
    return {}
    
"""