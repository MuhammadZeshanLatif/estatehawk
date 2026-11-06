import unittest

from app import quality


class MissingAddressTests(unittest.TestCase):
    def test_placeholder_address_is_reported_missing(self):
        parcel = {"is_active": 1, "last_seen": "2026-11-07", "street": "Index Order",
                  "owner_name": "Duke Energy Ohio Inc", "appraised_total": 16000000,
                  "amount_owed": 116246.83}
        county = {"last_sync": "2026-11-07", "host": "file:hamilton"}
        result = quality.lead(parcel, county)
        self.assertEqual(result["status"], "partial")
        self.assertIn("Street address", result["missing"])
        self.assertIn("Map location", result["missing"])


if __name__ == "__main__":
    unittest.main()
