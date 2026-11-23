import base64
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from starlette.requests import Request

from app import content, db, site, static_site

PNG = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 64).decode()


class StaticSiteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_path, self.old_con = db.DB_PATH, db._con
        db.DB_PATH, db._con = str(Path(self.temp.name) / "test.db"), None
        db.con()
        self.env = patch.dict(os.environ, {"APP_URL": "https://app.getestatehawk.com"})
        self.env.start()
        os.environ.pop("SITE_URL", None)

    def tearDown(self):
        self.env.stop()
        db._con.close()
        db.DB_PATH, db._con = self.old_path, self.old_con
        self.temp.cleanup()

    def build(self):
        out = str(Path(self.temp.name) / "site")
        static_site.build(out)
        return Path(out)

    def test_pages_links_media_and_htaccess(self):
        url = content.upload_image(PNG, "Cover shot.png")
        content.save({"title": "County lists", "slug": "county-lists", "description": "Guide", "body": "## Start\nRead it.",
                      "hero_image": url, "hero_alt": "A county record", "status": "published"})
        content.save({"title": "Hidden draft", "slug": "hidden-draft", "body": "Not yet.", "status": "draft"})
        out = self.build()
        article = (out / "blog" / "county-lists.html").read_text(encoding="utf-8")
        self.assertIn("Read it.", article)
        self.assertIn('<link rel="canonical" href="https://getestatehawk.com/blog/county-lists">', article)
        self.assertIn('href="https://app.getestatehawk.com/signup"', article)
        self.assertNotIn('href="/login"', article)
        self.assertTrue((out / url.lstrip("/")).is_file())
        self.assertFalse((out / "blog" / "hidden-draft.html").exists())
        self.assertFalse((out / "login.html").exists())
        self.assertFalse((out / "signup.html").exists())
        sitemap = (out / "sitemap.xml").read_text(encoding="utf-8")
        self.assertIn("/blog/county-lists", sitemap)
        self.assertNotIn("/signup", sitemap)
        contact = (out / "contact.html").read_text(encoding="utf-8")
        self.assertIn('data-api="https://app.getestatehawk.com/api/public/contact"', contact)
        widget = (out / "static" / "chat-widget.js").read_text(encoding="utf-8")
        self.assertIn("https://app.getestatehawk.com/api/public/chat", widget)
        self.assertNotIn("/api/auth/me", widget)
        htaccess = (out / ".htaccess").read_text(encoding="utf-8")
        self.assertIn("https://app.getestatehawk.com%{REQUEST_URI}", htaccess)
        self.assertIn("RewriteRule ^(.+)$ $1.html [L]", htaccess)
        self.assertTrue((out / "404.html").is_file() and (out / "index.html").is_file())

    def test_build_needs_separate_app_url(self):
        with patch.dict(os.environ, {"APP_URL": ""}):
            with self.assertRaises(SystemExit):
                self.build()

    def test_rebuild_request_is_quiet_without_settings(self):
        with patch.dict(os.environ, {"SITE_PUBLISH_TOKEN": "", "SITE_PUBLISH_REPO": ""}):
            self.assertFalse(static_site.request_rebuild())


class HostRoutingTests(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from app.main import app
        self.client = TestClient(app)

    def get(self, host, path):
        return self.client.get(path, headers={"host": host}, follow_redirects=False)

    def test_without_app_url_nothing_changes(self):
        with patch.dict(os.environ, {"APP_URL": ""}):
            r = self.get("estatehawk.onrender.com", "/login")
            self.assertEqual(r.headers["location"], "https://getestatehawk.com/login")

    def test_with_app_url_pages_go_to_the_right_host(self):
        with patch.dict(os.environ, {"APP_URL": "https://app.getestatehawk.com"}):
            self.assertEqual(self.get("app.getestatehawk.com", "/pricing").headers["location"], "https://getestatehawk.com/pricing")
            self.assertEqual(self.get("estatehawk.onrender.com", "/app").headers["location"], "https://app.getestatehawk.com/app")
            self.assertEqual(self.get("estatehawk.onrender.com", "/blog").headers["location"], "https://getestatehawk.com/blog")
            self.assertEqual(self.get("getestatehawk.com", "/login?x=1").headers["location"], "https://app.getestatehawk.com/login?x=1")
            self.assertEqual(self.get("app.getestatehawk.com", "/healthz").status_code, 200)

    def test_public_api_allows_website_origin(self):
        r = self.client.options("/api/public/contact", headers={"origin": "https://getestatehawk.com", "access-control-request-method": "POST"})
        self.assertEqual(r.status_code, 204)
        self.assertEqual(r.headers["access-control-allow-origin"], "https://getestatehawk.com")
        r = self.client.options("/api/public/contact", headers={"origin": "https://evil.example", "access-control-request-method": "POST"})
        self.assertNotIn("access-control-allow-origin", r.headers)


if __name__ == "__main__":
    unittest.main()
