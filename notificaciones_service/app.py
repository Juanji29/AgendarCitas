"""Microservicio de Notificaciones (Strangler Pattern).

Extrae la lógica de notificaciones del monolito Django y la expone como una
API REST en Flask. No accede a la base de datos: recibe los datos de la cita
por JSON y se encarga de generar/enviar la notificación de confirmación.
"""
import logging
import os
import smtplib
from email.mime.text import MIMEText

from flask import Flask, jsonify, request

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("notificaciones")

# Configuración vía variables de entorno (12-factor).
# Si SMTP no está configurado, el servicio degrada a modo consola.
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "25"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "no-reply@healthbook.local")

CAMPOS_REQUERIDOS = [
    "paciente_nombre",
    "medico_nombre",
    "especialidad",
    "fecha",
    "hora",
]


class ErrorValidacion(Exception):
    """Datos de entrada inválidos -> HTTP 400."""


def _validar_payload(datos):
    if not isinstance(datos, dict):
        raise ErrorValidacion("El cuerpo debe ser un objeto JSON.")

    faltantes = [c for c in CAMPOS_REQUERIDOS if not datos.get(c)]
    if faltantes:
        raise ErrorValidacion(
            "Faltan campos requeridos: " + ", ".join(faltantes)
        )


def _construir_mensaje(datos):
    return (
        f"Hola {datos['paciente_nombre']}, tu cita con {datos['medico_nombre']} "
        f"({datos['especialidad']}) quedó agendada para el {datos['fecha']} "
        f"a las {datos['hora']}."
    )


def _enviar_email(destinatario, asunto, cuerpo):
    """Envía el correo por SMTP. Si no hay SMTP configurado, lo registra en consola."""
    if not SMTP_HOST:
        logger.info("[Notificación consola] Para %s: %s", destinatario, cuerpo)
        return "consola"

    mensaje = MIMEText(cuerpo, "plain", "utf-8")
    mensaje["Subject"] = asunto
    mensaje["From"] = FROM_EMAIL
    mensaje["To"] = destinatario

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as servidor:
        if SMTP_USER:
            servidor.starttls()
            servidor.login(SMTP_USER, SMTP_PASSWORD)
        servidor.sendmail(FROM_EMAIL, [destinatario], mensaje.as_string())
    return "email"


@app.get("/health")
def health():
    """Healthcheck para Docker/Nginx."""
    return jsonify(status="ok", service="notificaciones"), 200


@app.post("/api/v2/notificaciones/confirmacion")
def notificar_confirmacion():
    """Recibe los datos de una cita y envía la notificación de confirmación."""
    datos = request.get_json(silent=True)
    _validar_payload(datos)

    asunto = "Confirmación de cita médica"
    cuerpo = _construir_mensaje(datos)
    destinatario = datos.get("paciente_email", "")

    if not destinatario:
        # Sin email no se envía nada, pero no es un error del cliente.
        logger.info("Cita sin email; no se envía notificación.")
        return jsonify(
            enviado=False,
            motivo="La cita no tiene email de paciente.",
        ), 200

    canal = _enviar_email(destinatario, asunto, cuerpo)
    return jsonify(
        enviado=True,
        canal=canal,
        destinatario=destinatario,
        mensaje=cuerpo,
    ), 200


@app.errorhandler(ErrorValidacion)
def manejar_error_validacion(error):
    return jsonify(error="bad_request", detalle=str(error)), 400


@app.errorhandler(500)
def manejar_error_interno(error):
    logger.exception("Error interno en el servicio de notificaciones")
    return jsonify(error="internal_server_error", detalle=str(error)), 500


@app.errorhandler(Exception)
def manejar_excepcion_no_controlada(error):
    logger.exception("Excepción no controlada")
    return jsonify(error="internal_server_error", detalle=str(error)), 500


if __name__ == "__main__":
    puerto = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=puerto)
