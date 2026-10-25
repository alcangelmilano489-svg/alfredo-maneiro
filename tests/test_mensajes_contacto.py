import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Dummy values ensure tests never contact the real Supabase project.
os.environ["SUPABASE_URL"] = "https://example.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "test-anon-key"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "test-service-role-key"
os.environ["ADMIN_PASSWORD"] = "test-admin-password"

import servidor  # noqa: E402


class MensajesContactoApiTests(unittest.TestCase):
    def setUp(self):
        servidor.supabase_admin = object()
        servidor.SUPABASE_WRITE_KEY = "sb_secret_test-key"
        self.client = servidor.app.test_client()
        self.payload = {
            "nombre_completo": "María Elena",
            "apellido": "Pérez Gómez",
            "email": "MARIA@example.org",
            "telefono": "+58 412 555 0101",
            "mensaje": "Quisiera recibir información.",
            "sitio_web": "",
        }

    def test_valid_message_is_saved_privately_and_response_has_no_pii(self):
        with patch.object(servidor, "solicitar_supabase_admin", return_value=[]) as save:
            response = self.client.post("/api/mensajes-contacto", json=self.payload)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json(), {"success": True})
        save.assert_called_once()
        args = save.call_args
        self.assertEqual(args.args[:2], ("POST", "mensajes_contacto"))
        self.assertEqual(args.kwargs["json"], {
            "nombre_completo": "María Elena",
            "apellido": "Pérez Gómez",
            "email": "maria@example.org",
            "telefono": "+58 412 555 0101",
            "mensaje": "Quisiera recibir información.",
        })
        self.assertNotIn("maria@example.org", response.get_data(as_text=True))

    def test_honeypot_returns_success_without_saving(self):
        payload = {**self.payload, "sitio_web": "https://spam.example"}
        with patch.object(servidor, "solicitar_supabase_admin") as save:
            response = self.client.post("/api/mensajes-contacto", json=payload)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json(), {"success": True})
        save.assert_not_called()

    def test_rejects_invalid_email_phone_and_missing_fields(self):
        casos = (
            {**self.payload, "email": "no-es-correo"},
            {**self.payload, "telefono": "123"},
            {key: value for key, value in self.payload.items() if key != "apellido"},
        )
        for payload in casos:
            with self.subTest(payload=payload):
                with patch.object(servidor, "solicitar_supabase_admin") as save:
                    response = self.client.post("/api/mensajes-contacto", json=payload)
                self.assertEqual(response.status_code, 400)
                save.assert_not_called()

    def test_rejects_oversized_payload(self):
        payload = {**self.payload, "mensaje": "x" * 17000}
        with patch.object(servidor, "solicitar_supabase_admin") as save:
            response = self.client.post("/api/mensajes-contacto", json=payload)

        self.assertEqual(response.status_code, 413)
        save.assert_not_called()

    def test_unconfigured_storage_returns_service_unavailable(self):
        servidor.supabase_admin = None
        with patch.object(servidor, "solicitar_supabase_admin") as save:
            response = self.client.post("/api/mensajes-contacto", json=self.payload)

        self.assertEqual(response.status_code, 503)
        save.assert_not_called()

    def test_messages_have_no_public_listing_endpoint(self):
        response = self.client.get("/api/mensajes-contacto")
        self.assertEqual(response.status_code, 405)

    def test_admin_message_listing_requires_correct_password(self):
        with patch.object(servidor, "solicitar_supabase_admin") as query:
            response = self.client.get(
                "/api/admin/mensajes-contacto",
                headers={"X-Admin-Password": "incorrecta"},
            )

        self.assertEqual(response.status_code, 401)
        query.assert_not_called()

    def test_admin_message_listing_returns_private_page_without_cache(self):
        filas = [
            {
                "nombre_completo": "María Elena",
                "apellido": "Pérez",
                "email": "maria@example.org",
                "telefono": "+58 412 555 0101",
                "mensaje": "Primer mensaje.",
                "created_at": "2026-10-25T12:00:00+00:00",
            },
            {
                "nombre_completo": "Luis",
                "apellido": "Gómez",
                "email": "luis@example.org",
                "telefono": "+58 414 555 0202",
                "mensaje": "Segundo mensaje.",
                "created_at": "2026-10-24T12:00:00+00:00",
            },
        ]
        with patch.object(servidor, "solicitar_supabase_admin", return_value=filas) as query:
            response = self.client.get(
                "/api/admin/mensajes-contacto?limit=1&offset=0",
                headers={"X-Admin-Password": "test-admin-password"},
            )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["mensajes"], filas[:1])
        self.assertTrue(data["has_more"])
        self.assertEqual(data["next_offset"], 1)
        self.assertIn("no-store", response.headers.get("Cache-Control", ""))
        args = query.call_args
        self.assertEqual(args.args[:2], ("GET", "mensajes_contacto"))
        self.assertEqual(args.kwargs["params"]["select"], "nombre_completo,apellido,email,telefono,mensaje,created_at")
        self.assertEqual(args.kwargs["params"]["order"], "created_at.desc")
        self.assertEqual(args.kwargs["params"]["limit"], "2")
        self.assertEqual(args.kwargs["params"]["offset"], "0")

    def test_admin_message_listing_rejects_invalid_pagination(self):
        with patch.object(servidor, "solicitar_supabase_admin") as query:
            response = self.client.get(
                "/api/admin/mensajes-contacto?limit=0",
                headers={"X-Admin-Password": "test-admin-password"},
            )

        self.assertEqual(response.status_code, 400)
        query.assert_not_called()


if __name__ == "__main__":
    unittest.main()
