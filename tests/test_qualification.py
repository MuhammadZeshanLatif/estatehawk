import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException

from app import db, qualification


class QualificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_path, self.old_con = db.DB_PATH, db._con
        db.DB_PATH, db._con = str(Path(self.temp.name) / "test.db"), None
        db.con()

    def tearDown(self):
        db._con.close()
        db.DB_PATH, db._con = self.old_path, self.old_con
        self.temp.cleanup()

    def test_seller_interest_requires_recorded_owner_response_and_is_org_private(self):
        self.assertEqual(qualification.lead(1, "parcel-1")["interest"], "unknown")
        with self.assertRaises(HTTPException):
            qualification.set_lead(1, "parcel-1", "interested", "")
        qualification.set_lead(1, "parcel-1", "interested", "Owner said yes on call")
        self.assertEqual(qualification.lead(1, "parcel-1")["interest"], "interested")
        self.assertEqual(qualification.lead(2, "parcel-1")["interest"], "unknown")
        qualification.set_lead(1, "parcel-1", "do_not_contact", "Owner asked for no more calls")
        self.assertEqual(qualification.lead(1, "parcel-1")["interest"], "do_not_contact")

    def test_contact_verification_is_separate_from_seller_interest(self):
        self.assertEqual(qualification.contact(1, 99)["status"], "unverified")
        with self.assertRaises(HTTPException):
            qualification.set_contact(1, 99, "confirmed_owner", "")
        qualification.set_contact(1, 99, "confirmed_owner", "Owner confirmed their name")
        self.assertEqual(qualification.contact(1, 99)["status"], "confirmed_owner")
        self.assertEqual(qualification.contact(2, 99)["status"], "unverified")
        self.assertEqual(qualification.lead(1, "parcel-1")["interest"], "unknown")


if __name__ == "__main__":
    unittest.main()
