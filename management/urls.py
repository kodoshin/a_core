from django.urls import path
from .views import pricing_credits

urlpatterns = [
    path('', pricing_credits, name='pricing_credits'),
]
