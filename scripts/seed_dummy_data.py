from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import create_app
from app.extensions import db
from app.models import Appointment, Consent, Doctor, MedicalRecord, Patient, Prescription, User


def get_or_create_user(email: str, role: str, password: str) -> User:
    u = User.query.filter_by(email=email).first()
    if u is None:
        u = User(email=email, role=role)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
    else:
        u.role = role
        db.session.commit()
    return u


def ensure_patient(user: User, **kwargs) -> Patient:
    p = Patient.query.get(user.id)
    if p is None:
        p = Patient(user_id=user.id)
        db.session.add(p)
        db.session.commit()

    for k, v in kwargs.items():
        setattr(p, k, v)
    db.session.commit()
    return p


def ensure_doctor(user: User, specialization: str, hospital_id: str) -> Doctor:
    d = Doctor.query.get(user.id)
    if d is None:
        d = Doctor(user_id=user.id, specialization=specialization, hospital_id=hospital_id)
        db.session.add(d)
    else:
        d.specialization = specialization
        d.hospital_id = hospital_id

    db.session.commit()
    return d


def ensure_consent(patient_id: int, doctor_id: int, active: bool) -> Consent:
    c = Consent.query.filter_by(patient_id=patient_id, doctor_id=doctor_id).first()
    if c is None:
        c = Consent(patient_id=patient_id, doctor_id=doctor_id)
        db.session.add(c)

    if active:
        c.revoked_at = None
        c.granted_at = datetime.utcnow() - timedelta(days=3)
    else:
        c.revoked_at = datetime.utcnow() - timedelta(days=1)
        c.granted_at = datetime.utcnow() - timedelta(days=10)

    db.session.commit()
    return c


def ensure_appointment(patient_id: int, doctor_id: int, scheduled_at: datetime, status: str) -> Appointment:
    a = (
        Appointment.query.filter_by(patient_id=patient_id, doctor_id=doctor_id, scheduled_at=scheduled_at)
        .order_by(Appointment.id.asc())
        .first()
    )
    if a is None:
        a = Appointment(patient_id=patient_id, doctor_id=doctor_id, scheduled_at=scheduled_at, status=status)
        db.session.add(a)
    else:
        a.status = status

    db.session.commit()
    return a


def ensure_prescription(appointment_id: int, pharmacy_user_id: int, notes: str) -> Prescription:
    p = Prescription.query.filter_by(appointment_id=appointment_id).first()
    if p is None:
        p = Prescription(appointment_id=appointment_id)
        db.session.add(p)

    p.notes = notes
    p.pharmacy_id = str(pharmacy_user_id)
    p.fulfillment_status = "pending"
    p.delivery_status = "not_started"
    db.session.commit()
    return p


def ensure_record(patient_id: int, file_path: str, description: str) -> MedicalRecord:
    r = MedicalRecord.query.filter_by(patient_id=patient_id, file_path=file_path).first()
    if r is None:
        r = MedicalRecord(patient_id=patient_id, file_path=file_path, description=description)
        db.session.add(r)
        db.session.commit()
    return r


def main() -> None:
    os.environ.setdefault("FLASK_ENV", "development")

    app = create_app(os.getenv("FLASK_ENV", "development"))

    with app.app_context():
        db.create_all()

        print("[seed] Creating users...")

        admin = get_or_create_user("admin@example.com", "admin", "adminpass")
        pharmacy = get_or_create_user("pharmacy@example.com", "pharmacy", "pharmacypass")
        emergency = get_or_create_user("emergency@example.com", "emergency", "emergencypass")

        d1u = get_or_create_user("doctor1@example.com", "doctor", "doctorpass")
        d2u = get_or_create_user("doctor2@example.com", "doctor", "doctorpass")
        d3u = get_or_create_user("doctor3@example.com", "doctor", "doctorpass")

        d1 = ensure_doctor(d1u, "Cardiology", "HOSP-001")
        d2 = ensure_doctor(d2u, "Dermatology", "HOSP-001")
        d3 = ensure_doctor(d3u, "General Medicine", "HOSP-002")

        print("[seed] Creating patients...")
        patients = []
        bg = ["O+", "A+", "B+", "AB+", "O-"]
        allergies = ["Penicillin", "Peanuts", "Dust", "None", "Latex"]
        chronic = ["Hypertension", "Asthma", "Diabetes", "None", "Thyroid"]

        for i in range(1, 6):
            u = get_or_create_user(f"patient{i}@example.com", "patient", "patientpass")
            p = ensure_patient(
                u,
                dob=f"199{i}-01-0{i}",
                gender="F" if i % 2 == 0 else "M",
                blood_group=bg[i - 1],
                allergies=allergies[i - 1],
                chronic_conditions=chronic[i - 1],
                emergency_contacts=f"Contact{i}: +1-555-000{i}",
            )
            patients.append(p)

        print("[seed] Creating consents...")
        ensure_consent(patients[0].user_id, d1.user_id, active=True)
        ensure_consent(patients[0].user_id, d2.user_id, active=False)
        ensure_consent(patients[1].user_id, d1.user_id, active=True)
        ensure_consent(patients[2].user_id, d3.user_id, active=True)
        ensure_consent(patients[3].user_id, d2.user_id, active=True)

        print("[seed] Creating appointments...")
        now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        a1 = ensure_appointment(patients[0].user_id, d1.user_id, now + timedelta(days=1), "scheduled")
        a2 = ensure_appointment(patients[1].user_id, d1.user_id, now - timedelta(days=2), "completed")
        a3 = ensure_appointment(patients[2].user_id, d3.user_id, now + timedelta(days=3), "scheduled")
        a4 = ensure_appointment(patients[3].user_id, d2.user_id, now - timedelta(days=5), "completed")

        print("[seed] Creating prescriptions...")
        ensure_prescription(a2.id, pharmacy.id, "Topical cream once daily for 7 days")
        ensure_prescription(a4.id, pharmacy.id, "Antihistamine at night for 5 days")

        print("[seed] Creating sample records...")
        ensure_record(patients[0].user_id, "uploads/sample_record_patient1.txt", "Lab summary")
        ensure_record(patients[1].user_id, "uploads/sample_record_patient2.txt", "Imaging report")

        os.makedirs(os.path.join(app.root_path, "static", "uploads"), exist_ok=True)
        for path, content in [
            ("sample_record_patient1.txt", "Deterministic sample record for patient1\n"),
            ("sample_record_patient2.txt", "Deterministic sample record for patient2\n"),
        ]:
            abs_path = os.path.join(app.root_path, "static", "uploads", path)
            if not os.path.exists(abs_path):
                with open(abs_path, "w", encoding="utf-8") as f:
                    f.write(content)

        print("[seed] Done.")
        print("[seed] Accounts:")
        print("  admin@example.com / adminpass")
        print("  doctor1@example.com / doctorpass")
        print("  patient1@example.com / patientpass")
        print("  pharmacy@example.com / pharmacypass")
        print("  emergency@example.com / emergencypass")


if __name__ == "__main__":
    main()
