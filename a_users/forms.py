from django.forms import ModelForm
from django import forms
from django.contrib.auth.models import User
from .models import Profile
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
            'github_access_key': forms.TextInput(attrs={'autocomplete': 'off'}),
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

    class Meta:
        model = Profile
        fields = ['role', 'country', 'marketing_channel', 'accept_marketing_communication', 'accept_data_usage_policy','timezone', 'gmt_offset']
        widgets = {
            'role': forms.Select(attrs={'style': "color: black; font-weight: bold; font-family: 'DynaPuff';"}),
            'country': forms.Select(attrs={'style': "color: black; font-weight: bold; font-family: 'DynaPuff';"}),
            'marketing_channel': forms.Select(attrs={'style': "color: black;font-weight: bold; font-family: 'DynaPuff';"}),
            'accept_marketing_communication': forms.CheckboxInput(attrs={'style': "width: 20px;"}),
            'timezone': forms.HiddenInput(),
            'gmt_offset': forms.HiddenInput(),
            'accept_data_usage_policy': forms.CheckboxInput(attrs={'style': 'width: 20px;'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Si le profil a déjà été rempli, on retire le champ de la politique
        if self.instance and self.instance.pk and self.instance.profile_is_filled:
            self.fields.pop('accept_data_usage_policy', None)
        else:
            self.fields['accept_data_usage_policy'].label = mark_safe(
                "I accept the <a href='#' id='policy-link'>data usage policy</a>"
            )

        label_width = '250px'
        # On modifie le label de chaque champ pour inclure du style en ligne
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.label = mark_safe(
                    f"""<span style="color: black; font-weight: bold; font-family: 'DynaPuff';">{field.label}</span>"""
                )
            else:
                field.label = mark_safe(
                    f"""<span style="color: black; display: inline-block; width: {label_width}; font-weight: bold; font-family: 'DynaPuff';">{field.label}</span>"""
                )