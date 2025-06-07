from django.urls import path
from .views import sana_view

urlpatterns = [
    path('sana/', sana_view, name='sana_view'),
]