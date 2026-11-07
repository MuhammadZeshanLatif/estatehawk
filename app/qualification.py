"""Human-confirmed owner identity and selling intent, private to each company."""
from fastapi import HTTPException

from . import db, jobs

CONTACT_STATUS = {"unverified", "confirmed_owner", "wrong_contact"}
INTEREST = {"unknown", "interested", "maybe_later", "not_selling", "do_not_contact"}


def lead(org_id, parcel_id):
    return db.q1("SELECT interest,evidence,updated FROM lead_qualifications WHERE org_id=? AND parcel_id=?",
                 (org_id, parcel_id)) or {"interest": "unknown", "evidence": "", "updated": None}


def set_lead(org_id, parcel_id, interest, evidence):
    if interest not in INTEREST:
        raise HTTPException(400, "Choose a valid owner response.")
    evidence = str(evidence or "").strip()[:500]
    if interest != "unknown" and len(evidence) < 8:
        raise HTTPException(400, "Briefly record what the owner said and how you heard it.")
    db.run("INSERT OR REPLACE INTO lead_qualifications(org_id,parcel_id,interest,evidence,updated) VALUES(?,?,?,?,?)",
           (org_id, parcel_id, interest, evidence if interest != "unknown" else "", jobs.now()))
    return lead(org_id, parcel_id)


def contact(org_id, contact_id):
    return db.q1("SELECT status,evidence,updated FROM contact_reviews WHERE org_id=? AND contact_id=?",
                 (org_id, contact_id)) or {"status": "unverified", "evidence": "", "updated": None}


def set_contact(org_id, contact_id, status, evidence):
    if status not in CONTACT_STATUS:
        raise HTTPException(400, "Choose a valid contact result.")
    evidence = str(evidence or "").strip()[:500]
    if status != "unverified" and len(evidence) < 8:
        raise HTTPException(400, "Briefly record how you checked this contact.")
    db.run("INSERT OR REPLACE INTO contact_reviews(org_id,contact_id,status,evidence,updated) VALUES(?,?,?,?,?)",
           (org_id, contact_id, status, evidence if status != "unverified" else "", jobs.now()))
    return contact(org_id, contact_id)
