# Agendar Citas Médicas Healthbook

## Participantes
- Andrés Osorio
- Juan Esteban Jiménez
- Juan Pablo Gaviria

## Descripción
Este proyecto consiste en una aplicación web desarrollada con Django para gestionar y mostrar citas médicas de forma sencilla. La idea principal es ofrecer una base funcional para organizar información relacionada con la agenda de pacientes y profesionales de salud.

## Objetivo del proyecto
El objetivo de Healthbook es crear una interfaz básica donde se puedan visualizar citas médicas y preparar la estructura para futuras mejoras, como registro de pacientes, filtros por fecha, gestión de horarios y autenticación de usuarios.

## Funcionalidades actuales
- Visualización de una página de citas.
- Configuración básica de rutas en Django.
- Uso de plantillas para presentar información en la interfaz web.
- Estructura modular organizada en aplicaciones.
- Lineamiento SOLID

## Tecnologías utilizadas
- Python
- Django
- HTML
- SQLite

## Requisitos previos
Antes de ejecutar el proyecto, asegúrate de tener instalado:
- Python 3.x
- Django
- Un entorno de terminal como PowerShell, CMD o Git Bash

## Instalación y ejecución
1. Abre la carpeta del proyecto en tu terminal.
2. Asegúrate de estar dentro de la carpeta raíz del proyecto.
3. Ejecuta el siguiente comando para iniciar el servidor:
   ```bash
   python manage.py runserver
   ```
4. Abre tu navegador y visita:
   ```text
   http://127.0.0.1:8000/citas/agendar
   ```

## Estructura del proyecto
- AgendarCitasMedicas: contiene la configuración principal del proyecto Django.
- citas: aplicación donde se encuentran las vistas, plantillas y lógica relacionada con las citas.
- db.sqlite3: base de datos local del proyecto.
- manage.py: archivo principal para ejecutar comandos de Django.

## Notas
Este es un proyecto inicial y va a ampliarse con más funcionalidades en futuras versiones, como formularios de registro, administración de usuarios y visualización más avanzada de citas, asi como la creacion de las diferentes clases como paciente, medico, centro de atencion, especialidad, pago y horario
