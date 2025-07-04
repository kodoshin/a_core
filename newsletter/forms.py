from django import forms
from .models import Subscriber


class NewsletterSubscriptionForm(forms.ModelForm):
    class Meta:
        model = Subscriber
        fields = ['email']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'border rounded px-3 py-2 w-full',
                'placeholder': 'Your email address',
                'required': True
            }),
        }
        labels = {'email': ''}