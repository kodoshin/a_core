from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def popup_close(request):
    """
    Final step of the popup authentication flow.
    Displays a tiny HTML page that closes the popup and refreshes the opener.
    """
    return render(request, "popup_close.html")