from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def get_login_redirect_url(self, request):
        url = super().get_login_redirect_url(request)
        if request.GET.get('popup') == '1':
            delimiter = '&' if '?' in url else '?'
            return f"{url}{delimiter}popup=1"
        return url

    def get_connect_redirect_url(self, request, socialaccount):
        url = super().get_connect_redirect_url(request, socialaccount)
        if request.GET.get('popup') == '1':
            delimiter = '&' if '?' in url else '?'
            return f"{url}{delimiter}popup=1"
        return url