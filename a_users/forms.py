from django.forms import ModelForm
from django import forms
from django.contrib.auth.models import User
from .models import Profile, Region
from django.utils.safestring import mark_safe


        
class EmailForm(ModelForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['email']


class GithubKeyForm(ModelForm):
    class Meta:
        model = Profile
        fields = ['github_access_key']
        widgets = {
            'github_access_key': forms.TextInput(attrs={'autocomplete': 'off', "style": "height:10px"}),
        }

    def __init__(self, *args, **kwargs):
        original_key = ''
        if 'instance' in kwargs and kwargs['instance']:
            original_key = kwargs['instance'].github_access_key or ''
        # prepare masked initial
        initial = kwargs.get('initial', {})
        if original_key:
            masked = '*' * 10 + original_key[-3:]
            initial['github_access_key'] = masked
        kwargs['initial'] = initial
        super().__init__(*args, **kwargs)
        self._original_key = original_key

    def clean_github_access_key(self):
        data = self.cleaned_data.get('github_access_key', '')
        original = getattr(self, '_original_key', '')
        if original:
            masked = '*' * 10 + original[-3:]
            if data == masked:
                return original
        return data


class ProfileForm(forms.ModelForm):
    coupon_code = forms.CharField(
        max_length=50,
        required=False,
        label='Coupon',
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter your code',
            # largeur fixe, hauteur réduite, texte en noir
            'style': (
                'color: black; '
                'width: 160px; '  # adapte la largeur à tes besoins
                'height: 1.5em; '  # réduit la hauteur du champ
                'line-height: 1.5em;'  # centre verticalement le texte
            ),
            'size': '10',  # optionnel : nombre de caractères visibles
        })
    )

    class Meta:
        model = Profile
        fields = ['role', 'country', 'region', 'marketing_channel', #'accept_marketing_communication',
                  'accept_data_usage_policy','timezone', 'gmt_offset']
        widgets = {
            'role': forms.Select(attrs={'style': "color: black; font-weight: bold;"}),
            'country': forms.Select(attrs={'style': "color: black; font-weight: bold;"}),
            'region': forms.Select(attrs={
                'style': 'color: black; font-weight: bold;',
                'class': 'js-region-select'
            }),
            'marketing_channel': forms.Select(attrs={'style': "color: black;font-weight: bold;"}),
            #'accept_marketing_communication': forms.CheckboxInput(attrs={'style': "width: 20px;"}),
            'timezone': forms.HiddenInput(),
            'gmt_offset': forms.HiddenInput(),
            'accept_data_usage_policy': forms.CheckboxInput(attrs={'style': 'width: 20px;'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Si le profil a déjà été rempli, on retire le champ de la politique
        if self.instance and self.instance.pk and self.instance.profile_is_filled:
            for f in ['coupon_code', 'accept_data_usage_policy']:
                self.fields.pop(f, None)
        else:
            self.fields['accept_data_usage_policy'].label = mark_safe(
                "I accept the <a href='#' id='policy-link'>data usage policy</a>"
            )

        self.fields['country'].required = True
        if 'accept_data_usage_policy' in self.fields:
            self.fields['accept_data_usage_policy'].required = True


        label_width = '220px'
        # On modifie le label de chaque champ pour inclure du style en ligne
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.label = mark_safe(
                    f"""<span style="color: white; font-weight: bold;">{field.label}</span>"""
                )
            else:
                field.label = mark_safe(
                    f"""<span style="color: white; display: inline-block; width: {label_width}; font-weight: bold;">{field.label}</span>"""
                )

        # Filter region queryset based on country in POST or instance
        if self.data.get('country'):
            try:
                country_id = int(self.data.get('country'))
                self.fields['region'].queryset = Region.objects.filter(country_id=country_id)
            except (ValueError, TypeError):
                self.fields['region'].queryset = Region.objects.none()
        elif self.instance and self.instance.country:
            self.fields['region'].queryset = Region.objects.filter(country=self.instance.country)
        else:
            self.fields['region'].queryset = Region.objects.none()


