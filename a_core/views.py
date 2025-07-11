from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def popup_close(request):
    """
    Display a page that closes the authentication popup
    and refreshes its opener.
    """
    return render(request, "account/popup_close.html")