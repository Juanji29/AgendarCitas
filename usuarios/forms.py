from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password


class LoginForm(AuthenticationForm):
    username = forms.EmailField(label='Correo electrónico')


class RegistroForm(forms.Form):
    nombre = forms.CharField(label='Nombre', max_length=100)
    apellido = forms.CharField(label='Apellido', max_length=100)
    dni = forms.CharField(label='Documento', max_length=12)
    correo = forms.EmailField(label='Correo electrónico')
    telefono = forms.CharField(label='Teléfono', max_length=13)
    password = forms.CharField(label='Contraseña', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirmar contraseña', widget=forms.PasswordInput)

    def clean_correo(self):
        correo = self.cleaned_data['correo'].lower()
        if get_user_model().objects.filter(username=correo).exists():
            raise forms.ValidationError('Ya existe una cuenta con este correo.')
        return correo

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password2 = cleaned_data.get('password2')
        if password and password2 and password != password2:
            self.add_error('password2', 'Las contraseñas no coinciden.')
        if password:
            validate_password(password)
        return cleaned_data