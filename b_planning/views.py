from django.shortcuts import render
from django.http import JsonResponse


def sana_view(request):
    """
    Endpoint: /ai/sana
    Simple JSON response handled by the b_planning app.
    """
    if request.method == "GET":
        return JsonResponse({"message": "Bienvenue sur l'endpoint Sana !"})
    return JsonResponse({"error": "Méthode non autorisée"}, status=405)