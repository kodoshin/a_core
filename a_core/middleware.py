class PopupFlagMiddleware:
    """
    Save a flag in session when the flow is started with ?popup=1.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.GET.get('popup') == '1':
            print('Middleware works')
            request.session['auth_popup'] = True
        return self.get_response(request)