from django.contrib.auth import login, logout
from django.shortcuts import redirect, render

from .forms import LoginForm, RegistroForm
from .services import UsuarioService

def registro(request):
    form = RegistroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        usuario = UsuarioService.registrar_paciente(form.cleaned_data)
        login(request, usuario)
        return redirect("citas:agendar_cita")

    return render(request, "usuarios/registro.html", {"form": form})

def iniciar_sesion(request):
    form = LoginForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect("citas:agendar_cita")

    return render(request, "usuarios/login.html", {"form": form})

def cerrar_sesion(request):
    logout(request)
    return redirect("usuarios:login")