from django.urls import reverse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

class SocialAccountAdapter(DefaultSocialAccountAdapter):

    def _popup_flow(self, request):
        return request.session.pop("auth_popup", False)

    # after OAuth login
    def get_login_redirect_url(self, request):
        if self._popup_flow(request):
            return reverse("popup-close")
        return super().get_login_redirect_url(request)

    # after connecting another account
    def get_connect_redirect_url(self, request, socialaccount):
        if self._popup_flow(request):
            return reverse("popup-close")
        return super().get_connect_redirect_url(request, socialaccount)