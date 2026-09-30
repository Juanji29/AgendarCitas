# Monolito Django (Healthbook) - Strangler Pattern
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Recolecta los estáticos para que WhiteNoise los sirva en producción.
RUN python manage.py collectstatic --noinput

EXPOSE 8000

# gunicorn sirve la app WSGI del proyecto
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "AgendarCitasMedicas.wsgi:application"]
