from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _


class LoginForm(AuthenticationForm):
    username = forms.EmailField(label=_('Correo electrónico'))


class RegistroForm(forms.Form):
    nombre = forms.CharField(label=_('Nombre'), max_length=100)
    apellido = forms.CharField(label=_('Apellido'), max_length=100)
    dni = forms.CharField(label=_('Documento'), max_length=12)
    correo = forms.EmailField(label=_('Correo electrónico'))
    telefono = forms.CharField(label=_('Teléfono'), max_length=13)
    password = forms.CharField(label=_('Contraseña'), widget=forms.PasswordInput)
    password2 = forms.CharField(label=_('Confirmar contraseña'), widget=forms.PasswordInput)

    def clean_correo(self):
        correo = self.cleaned_data['correo'].lower()
        if get_user_model().objects.filter(username=correo).exists():
            raise forms.ValidationError(_('Ya existe una cuenta con este correo.'))
        return correo

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password2 = cleaned_data.get('password2')
        if password and password2 and password != password2:
            self.add_error('password2', _('Las contraseñas no coinciden.'))
        if password:
            validate_password(password)
        return cleaned_data