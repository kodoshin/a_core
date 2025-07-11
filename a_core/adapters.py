from django.urls import reverse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom adapter used to detect when the login / connect flow is
    happening inside a popup window (popup=1) and, once the authentication
    is completed, redirect to a dedicated view whose only purpose is to
    refresh the opener and close the popup.
    """

    def _popup_redirect(self, request) -> str:
        """
        Return the dedicated closing url when popup=1 is detected.
        """
        if request.GET.get("popup") == "1":
            return reverse("popup-close")
        return None

    # ----- OAuth login (new account or existing) --------------------------
    def get_login_redirect_url(self, request):
        popup_url = self._popup_redirect(request)
        if popup_url:
            return popup_url
        return super().get_login_redirect_url(request)

    # ----- Social account connect flow -----------------------------------
    def get_connect_redirect_url(self, request, socialaccount):
        popup_url = self._popup_redirect(request)
        if popup_url:
            return popup_url
        return super().get_connect_redirect_url(request, socialaccount)