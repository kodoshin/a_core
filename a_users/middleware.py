from django.shortcuts import redirect
from django.urls import reverse


class ProfileCompletionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/pricing/stripe/webhook/"):
            return self.get_response(request)
        if request.user.is_authenticated:
            ajax_url = reverse('ajax_load_regions')
            onboarding_url = reverse('profile-onboarding')
            # Skip completion check for onboarding page and AJAX regions endpoint
            if request.path not in (onboarding_url, ajax_url):
                if not request.user.is_superuser and request.user.profile.profile_is_filled == 0:
                    return redirect('profile-onboarding')
        response = self.get_response(request)
        return response