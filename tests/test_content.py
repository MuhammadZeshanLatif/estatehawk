import base64
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from starlette.requests import Request

from app import content, db, site


def request(path="/blog", query=b"", referer=""):
    headers = [(b"referer", referer.encode())] if referer else []
    return Request({"type": "http", "method": "GET", "path": path, "headers": headers,
                    "query_string": query, "scheme": "https", "server": ("getestatehawk.com", 443)})


class ContentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_path, self.old_con = db.DB_PATH, db._con
        db.DB_PATH, db._con = str(Path(self.temp.name) / "test.db"), None
        db.con()

    def tearDown(self):
        db._con.close()
        db.DB_PATH, db._con = self.old_path, self.old_con
        self.temp.cleanup()

    def test_draft_preview_publish_and_sitemap(self):
        data = {"title": "Reading county tax lists", "slug": "reading-county-tax-lists",
                "description": "A practical guide", "body": "## Start here\nRead the county record first.", "status": "draft"}
        item = content.save(data)
        self.assertIsNone(site.render(request(), "blog/reading-county-tax-lists"))
        self.assertNotIn("reading-county-tax-lists", site.sitemap(request()))
        html = site.blog_article(request(), item["slug"], item)
        self.assertIn("Read the county record", html)
        data["status"] = "published"
        content.save(data, item["id"])
        self.assertIn("reading-county-tax-lists", site.sitemap(request()))
        self.assertIn('"@type":"BlogPosting"', site.render(request(), "blog/reading-county-tax-lists"))

    def test_body_escapes_script_and_slug_collision(self):
        self.assertIn("&lt;script&gt;", content.body_html("<script>alert(1)</script>"))
        data = {"title": "One", "slug": "same", "body": "Body", "status": "draft"}
        content.save(data)
        with self.assertRaises(HTTPException) as caught:
            content.save(data)
        self.assertEqual(caught.exception.status_code, 409)

    def test_cover_upload_rejects_non_images_and_requires_alt(self):
        with self.assertRaises(HTTPException):
            content.upload_image(base64.b64encode(b"<script>bad</script>").decode())
        url = content.upload_image(base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 40).decode())
        self.assertRegex(url, r"^/blog-media/\d+$")
        with self.assertRaises(HTTPException):
            content.save({"title": "Cover", "slug": "cover", "body": "Body", "hero_image": url})

    def test_first_source_stays_with_visitor_through_funnel(self):
        visit = request("/blog", b"utm_source=google&utm_medium=organic")
        content.track(visit, "landed", "a" * 32)
        content.track(request("/signup"), "signup", "a" * 32)
        content.track(request("/verify-email"), "verified", "a" * 32)
        rows = content.funnel(30)["rows"]
        google_blog = next(r for r in rows if r["source"] == "Google organic" and r["entry_type"] == "blog")
        self.assertEqual([google_blog[k] for k in ("landed", "signup", "verified", "paid")], [1, 1, 1, 0])
        content.track(request("/signup"), "signup", "a" * 32)
        self.assertEqual(content.funnel(30)["totals"]["signup"], 1)


if __name__ == "__main__":
    unittest.main()
