import unittest
import asyncio
from unittest.mock import patch

from starlette.requests import Request
from starlette.responses import Response

from app import auth, site


class SignupSecurityTests(unittest.TestCase):
    def test_password_policy(self):
        for value in ("abc123!", "abcdefghi", "123456789!", "Abcdefghi1"):
            self.assertIsNotNone(auth.password_error(value))
        self.assertIsNone(auth.password_error("CorrectHorse1!"))
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


if __name__ == "__main__":
    unittest.main()
