import os
import unittest
from unittest.mock import Mock, patch

from app import ai


class GeminiFallbackTests(unittest.TestCase):
    @patch.dict(os.environ, {"GEMINI_API_KEY": "primary", "GEMINI_API_KEY_BACKUP": "backup"})
    @patch("app.ai.requests.post")
    def test_uses_backup_after_primary_failure(self, post):
        post.side_effect = [Mock(status_code=429, text="quota"),
                            Mock(status_code=200, json=lambda: {"candidates": [{"content": {"parts": [{"text": "OK"}]}}]})]
        self.assertEqual(ai.generate("test"), "OK")
        self.assertEqual([c.kwargs["params"]["key"] for c in post.call_args_list], ["primary", "backup"])

    @patch.dict(os.environ, {"GEMINI_API_KEY": "same", "GEMINI_API_KEY_BACKUP": "same"})
    @patch("app.ai.requests.post")
    def test_duplicate_key_is_not_retried(self, post):
        post.return_value = Mock(status_code=200, json=lambda: {"candidates": [{"content": {"parts": [{"text": "OK"}]}}]})
        self.assertEqual(ai.generate("test"), "OK")
        self.assertEqual(post.call_count, 1)

    @patch.dict(os.environ, {"GEMINI_API_KEY": "primary", "GEMINI_API_KEY_BACKUP": "backup"})
    @patch("app.ai.requests.post")
    def test_offer_uses_template_when_both_keys_fail(self, post):
        post.return_value = Mock(status_code=429, text="quota")
        parcel = {"owner_name": "DOE JANE", "street": "123 Main St", "city": "Lima"}
        terms = {"price": 10000, "financing": "Cash", "closing_days": 21, "seller_credits": "None", "earnest": 1000}
        subject, body, source = ai.offer(parcel, terms, {"name": "Buyer"})
        self.assertTrue(subject)
        self.assertIn("$10,000", body)
        self.assertTrue(source.startswith("template"))
        self.assertEqual(post.call_count, 2)


if __name__ == "__main__":
    unittest.main()
