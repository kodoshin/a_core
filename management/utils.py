from django.db import transaction
from django.db.models import F
from .models import APIKey

def get_api_key(key_type):
    """
    Atomically select the active APIKey with the lowest real_time_users and increment its counter.
    """
    with transaction.atomic():
        key = APIKey.objects.filter(is_active=True, key_type=key_type) \
            .order_by('real_time_users', 'created_at') \
            .select_for_update().first()
        if key:
            APIKey.objects.filter(pk=key.pk).update(real_time_users=F('real_time_users') + 1)
        return key

def release_api_key(key):
    """
    Decrement the real_time_users counter when a request is done.
    """
    APIKey.objects.filter(pk=key.pk).update(real_time_users=F('real_time_users') - 1)