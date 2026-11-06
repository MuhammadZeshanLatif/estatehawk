import unittest
import asyncio
from unittest.mock import patch

from starlette.requests import Request
from starlette.responses import Response

from app import auth, site
from app.main import _optional_phone
from app import main
from fastapi import HTTPException


class SignupSecurityTests(unittest.TestCase):
    def test_password_policy(self):
        for value in ("abc123!", "abcdefghi", "123456789!", "password123456789"):
            self.assertIsNotNone(auth.password_error(value))
        self.assertIsNone(auth.password_error("Correct Horse Battery"))
        self.assertIsNotNone(auth.password_error("A1!" + "x" * 126))

    def test_signup_and_reset_have_confirm_and_reveal_controls(self):
        for prefix in ("s", "r"):
            fields = site.password_fields(prefix)
            self.assertIn('name="confirm_password"', fields)
            self.assertIn(f'data-toggle-password="{prefix}-pw"', fields)
            self.assertIn(f'data-toggle-password="{prefix}-confirm"', fields)

    def test_unconfirmed_account_cannot_call_dashboard_api(self):
        request = Request({"type": "http", "method": "GET", "path": "/api/parcels", "headers": [], "query_string": b"", "scheme": "https", "server": ("test", 443)})
        async def next_handler(_):
            return Response("private data")
        with patch("app.auth.current", return_value={"id": 7, "role": "admin", "email_verified": 0}):
            response = asyncio.run(auth.middleware(request, next_handler))
        self.assertEqual(response.status_code, 403)
        self.assertIn(b"email_verification_required", response.body)

    def test_phone_is_optional_but_must_be_plausible(self):
        self.assertEqual(_optional_phone(""), "")
        self.assertEqual(_optional_phone(" +92 341 1234567 "), "+92 341 1234567")
        with self.assertRaises(HTTPException):
            _optional_phone("abc")

    def test_contact_message_is_saved_for_admin_even_if_email_fails(self):
        request = Request({"type": "http", "method": "POST", "path": "/api/public/contact", "headers": [], "query_string": b"", "scheme": "https", "server": ("test", 443)},
                          receive=lambda: self._body())
        with patch("app.main._client_ip", return_value="127.0.0.1"), patch("app.main.auth.throttle"), patch("app.main.auth.failed"), patch("app.main.auth.audit"), patch("app.main.mailer.send", return_value=False), patch("app.main.db.run") as run:
            result = asyncio.run(main.public_contact(request))
        self.assertEqual(result, {"ok": True})
        self.assertIn("contact_messages", run.call_args.args[0])

    async def _body(self):
        return {"type": "http.request", "body": b'{"name":"Sam","email":"sam@example.com","phone":"+1 555 123 4567","message":"Please help"}', "more_body": False}


if __name__ == "__main__":
    unittest.main()
