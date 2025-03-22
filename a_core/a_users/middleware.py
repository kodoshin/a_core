from django.shortcuts import redirect
from django.urls import reverse


class ProfileCompletionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Proceed only if the user is authenticated and the request is not targeting the onboarding page
        if request.user.is_authenticated:
            onboarding_url = reverse('profile-onboarding')
            if request.path != onboarding_url:
                # If the profile is not completed, redirect to the onboarding page
                if request.user.profile.profile_is_filled == 0:
                    return redirect('profile-onboarding')
        response = self.get_response(request)
        return response