"""Pruebas del microservicio de Catálogo."""
import json
import os
import tempfile
import unittest


class CatalogoServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Base de datos y semilla temporales, aisladas del entorno.
        cls.tmpdir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.tmpdir, "catalogo_test.sqlite3")
        cls.seed_path = os.path.join(cls.tmpdir, "seed.json")

        fixture = [
            {"model": "citas.especialidad", "pk": 1, "fields": {
                "nombre": "cardiologia", "duracion_minutos": 30,
                "requiere_referido": True, "activa": True}},
            {"model": "citas.especialidad", "pk": 2, "fields": {
                "nombre": "pediatria", "duracion_minutos": 25,
                "requiere_referido": False, "activa": True}},
            {"model": "citas.especialidad", "pk": 3, "fields": {
                "nombre": "oculta", "duracion_minutos": 15,
                "requiere_referido": False, "activa": False}},
        ]
        with open(cls.seed_path, "w", encoding="utf-8") as fh:
            json.dump(fixture, fh)

        os.environ["CATALOGO_DB_PATH"] = cls.db_path
        os.environ["CATALOGO_SEED_PATH"] = cls.seed_path

        import app as catalogo_app  # import tras fijar env
        cls.module = catalogo_app
        cls.app = catalogo_app.app
        cls.client = cls.app.test_client()

    def test_health_ok(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["status"], "ok")

    def test_lista_solo_activas_ordenadas_por_id(self):
        resp = self.client.get("/api/v2/catalogo/especialidades")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["data"]
        ids = [e["id"] for e in data]
        self.assertEqual(ids, [1, 2])  # la inactiva (3) no aparece
        self.assertEqual(data[0]["nombre"], "cardiologia")
        self.assertIs(data[0]["requiere_referido"], True)

    def test_obtener_por_id_existente(self):
        resp = self.client.get("/api/v2/catalogo/especialidades/2")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["data"]["nombre"], "pediatria")

    def test_obtener_inactiva_es_404(self):
        resp = self.client.get("/api/v2/catalogo/especialidades/3")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.get_json()["error"], "not_found")

    def test_obtener_inexistente_es_404(self):
        resp = self.client.get("/api/v2/catalogo/especialidades/999")
        self.assertEqual(resp.status_code, 404)

    def test_id_no_numerico_es_404(self):
        resp = self.client.get("/api/v2/catalogo/especialidades/abc")
        self.assertEqual(resp.status_code, 404)

    def test_seed_es_idempotente_upsert_por_id(self):
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            self.module.seed_db(conn, self.seed_path)  # re-sembrar
            total = conn.execute("SELECT COUNT(*) AS c FROM especialidad").fetchone()["c"]
        finally:
            conn.close()
        self.assertEqual(total, 3)  # no se duplican filas


if __name__ == "__main__":
    unittest.main()
