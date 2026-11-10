"""Microservicio de Catálogo (Strangler Pattern).

Extrae el catálogo de especialidades del monolito Django a un microservicio
Flask con **base de datos propia** (SQLite independiente). Implementa el
contrato definido en ``docs/contratos_api.md``:

- GET /api/v2/catalogo/especialidades
- GET /api/v2/catalogo/especialidades/<int:id>
- GET /health

La base de datos se siembra al arrancar a partir de un fixture exportado del
monolito (upsert por id), conservando los IDs originales.
"""
import json
import logging
import os
import sqlite3
from pathlib import Path

from flask import Flask, g, jsonify

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("catalogo")

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = os.getenv("CATALOGO_DB_PATH", str(BASE_DIR / "catalogo.sqlite3"))
SEED_PATH = os.getenv("CATALOGO_SEED_PATH", str(BASE_DIR / "data" / "especialidades.json"))

CAMPOS = ("id", "nombre", "duracion_minutos", "requiere_referido", "activa")


def get_db():
    """Conexión SQLite por request (base de datos propia del catálogo)."""
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(db):
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS especialidad (
            id INTEGER PRIMARY KEY,
            nombre TEXT NOT NULL,
            duracion_minutos INTEGER NOT NULL,
            requiere_referido INTEGER NOT NULL DEFAULT 0,
            activa INTEGER NOT NULL DEFAULT 1
        )
        """
    )
    db.commit()


def _registros_desde_fixture(ruta):
    """Lee el fixture de Django (model/pk/fields) y lo normaliza a filas."""
    path = Path(ruta)
    if not path.exists():
        logger.warning("Fixture de catálogo no encontrado en %s", ruta)
        return []

    contenido = json.loads(path.read_text(encoding="utf-8"))
    filas = []
    for item in contenido:
        campos = item.get("fields", {})
        filas.append(
            {
                "id": item["pk"],
                "nombre": campos.get("nombre", ""),
                "duracion_minutos": int(campos.get("duracion_minutos", 0)),
                "requiere_referido": 1 if campos.get("requiere_referido") else 0,
                "activa": 1 if campos.get("activa", True) else 0,
            }
        )
    return filas


def seed_db(db, ruta=None):
    """Upsert por id: actualiza registros existentes, inserta los nuevos."""
    filas = _registros_desde_fixture(ruta or SEED_PATH)
    for fila in filas:
        db.execute(
            """
            INSERT INTO especialidad (id, nombre, duracion_minutos, requiere_referido, activa)
            VALUES (:id, :nombre, :duracion_minutos, :requiere_referido, :activa)
            ON CONFLICT(id) DO UPDATE SET
                nombre=excluded.nombre,
                duracion_minutos=excluded.duracion_minutos,
                requiere_referido=excluded.requiere_referido,
                activa=excluded.activa
            """,
            fila,
        )
    db.commit()
    return len(filas)


def _bootstrap():
    """Crea el esquema y siembra la base de datos propia del servicio."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn)
        total = seed_db(conn)
        logger.info("Catálogo sembrado con %s especialidades.", total)
    finally:
        conn.close()


def _fila_a_dict(fila):
    return {
        "id": fila["id"],
        "nombre": fila["nombre"],
        "duracion_minutos": fila["duracion_minutos"],
        "requiere_referido": bool(fila["requiere_referido"]),
        "activa": bool(fila["activa"]),
    }


@app.get("/health")
def health():
    """Healthcheck: verifica que la base de datos propia responde."""
    try:
        get_db().execute("SELECT 1").fetchone()
    except sqlite3.Error:
        return jsonify(error="service_unavailable", detail="El catálogo no está listo."), 503
    return jsonify(status="ok", service="catalogo"), 200


@app.get("/api/v2/catalogo/especialidades")
def listar_especialidades():
    try:
        filas = get_db().execute(
            "SELECT id, nombre, duracion_minutos, requiere_referido, activa "
            "FROM especialidad WHERE activa = 1 ORDER BY id"
        ).fetchall()
    except sqlite3.Error:
        return jsonify(
            error="service_unavailable",
            detail="El catálogo no está disponible temporalmente.",
        ), 503
    return jsonify(data=[_fila_a_dict(f) for f in filas]), 200


@app.get("/api/v2/catalogo/especialidades/<int:especialidad_id>")
def obtener_especialidad(especialidad_id):
    try:
        fila = get_db().execute(
            "SELECT id, nombre, duracion_minutos, requiere_referido, activa "
            "FROM especialidad WHERE id = ? AND activa = 1",
            (especialidad_id,),
        ).fetchone()
    except sqlite3.Error:
        return jsonify(
            error="service_unavailable",
            detail="El catálogo no está disponible temporalmente.",
        ), 503

    if fila is None:
        return jsonify(
            error="not_found",
            detail="No se encontró una especialidad activa con ese id.",
        ), 404
    return jsonify(data=_fila_a_dict(fila)), 200


# Siembra la base de datos al importar el módulo (arranque con gunicorn).
_bootstrap()


if __name__ == "__main__":
    puerto = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=puerto)
