import unittest
from unittest.mock import patch

from starlette.requests import Request

from app import main, site


def request(path):
    return Request({"type": "http", "method": "GET", "path": path, "headers": [],
                    "query_string": b"", "scheme": "https", "server": ("getestatehawk.com", 443)})


class MarketingSessionTests(unittest.TestCase):
    def test_signed_in_header_shows_account_and_dashboard_not_signup(self):
        user = {"name": "Muhammad Zeeshan", "email_verified": 1, "has_avatar": 0}
        header = site.header("features", user)
        self.assertIn("Hi, Muhammad", header)
        self.assertIn("Open dashboard", header)
        self.assertNotIn("Start free trial", header)
        self.assertNotIn('href="/login"', header)

    def test_unconfirmed_header_sends_user_to_confirmation(self):
        header = site.header("", {"name": "Farhan", "email_verified": 0})
        self.assertIn('href="/check-email"', header)
        self.assertNotIn('href="/signup"', header)

    def test_login_and_signup_redirect_when_session_is_valid(self):
        with patch("app.main.auth.current", return_value={"id": 1, "email_verified": 1}):
            for path in ("login", "signup"):
                response = main.spa(path, request("/" + path))
                self.assertEqual(response.status_code, 303)
                self.assertEqual(response.headers["location"], "/app#/deals")

    def test_signed_in_marketing_page_is_private_and_uses_session(self):
        user = {"id": 1, "email_verified": 1, "name": "Zeeshan"}
        with patch("app.main.auth.current", return_value=user), patch("app.main.site.render", return_value="<html>signed in</html>"), patch("app.main.content.track_safely"):
            response = main.spa("features", request("/features"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "private, no-store")
        self.assertEqual(response.headers["vary"], "Cookie")


if __name__ == "__main__":
    unittest.main()
