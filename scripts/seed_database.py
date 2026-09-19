import sys
from pathlib import Path

# Add project root to sys.path so "from app import ..." works
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from app.extensions import db
from app.models.user import User, Role
from app.models.parking_bay import ParkingBay, BayStatus
from app.models.tariff import Tariff
from app.models.setting import SystemSetting


def get_or_create_role(name):
    r = Role.query.filter_by(name=name).first()
    if not r:
        r = Role(name=name)
        db.session.add(r)
        db.session.flush()
    return r


def get_or_create_user(username, full_name, role_name, password):
    u = User.query.filter_by(username=username).first()
    if u:
        return u
    role = get_or_create_role(role_name)
    u = User(username=username, full_name=full_name, role_id=role.id)
    u.set_password(password)
    db.session.add(u)
    return u


def main():
    app = create_app()
    with app.app_context():
        db.create_all()

        # Roles
        get_or_create_role("admin")
        get_or_create_role("attendant")
        get_or_create_role("auditor")
        db.session.commit()

        # Users
        get_or_create_user("admin", "System Administrator", "admin", "ChangeMe123!")
        get_or_create_user("attendant", "Mary Wanjiku", "attendant", "ChangeMe123!")
        get_or_create_user("auditor", "John Otieno", "auditor", "ChangeMe123!")
        db.session.commit()

        # Bays
        if ParkingBay.query.count() == 0:
            for zone, prefix in (("A", "A"), ("B", "B")):
                for i in range(1, 11):
                    number = f"{prefix}{i:02d}"
                    priority = (zone == "A" and i <= 2)
                    db.session.add(ParkingBay(
                        bay_number=number, zone=zone,
                        status=BayStatus.AVAILABLE, is_priority=priority))
            db.session.commit()

        # Tariffs
        if Tariff.query.count() == 0:
            bands = [
                ("Up to 30 minutes (FREE)", 30, 0.0),
                ("Up to 2 hours", 120, 50.0),
                ("Up to 4 hours", 240, 100.0),
                ("Up to 6 hours", 360, 300.0),
                ("Over 6 hours", 999999, 500.0),
            ]
            for name, mx, amt in bands:
                db.session.add(Tariff(name=name, max_duration_minutes=mx,
                                      amount=amt, is_active=True))
            db.session.commit()

        # Settings
        if not SystemSetting.query.filter_by(setting_key="vat_rate").first():
            SystemSetting.set("vat_rate", "16", "VAT rate (%) applied to parking fees.")
        if not SystemSetting.query.filter_by(setting_key="site_name").first():
            SystemSetting.set("site_name", "Modern Parking Management System", "")

        print("[OK] Database seeded successfully.")
        print(f"     Users:   {User.query.count()}")
        print(f"     Bays:    {ParkingBay.query.count()}")
        print(f"     Tariffs: {Tariff.query.count()}")
        print()
        print("     Login credentials:")
        print("       admin      / ChangeMe123!")
        print("       attendant  / ChangeMe123!")
        print("       auditor    / ChangeMe123!")
        print("     CHANGE THESE PASSWORDS after first login.")


if __name__ == "__main__":
    main()