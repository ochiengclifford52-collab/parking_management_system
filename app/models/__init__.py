"""Import all models so SQLAlchemy knows about them."""
from .user import User, Role
from .vehicle import Vehicle
from .parking_bay import ParkingBay
from .parking_session import ParkingSession
from .tariff import Tariff
from .payment import Payment
from .audit_log import AuditLog
from .setting import SystemSetting

__all__ = ["User", "Role", "Vehicle", "ParkingBay", "ParkingSession",
           "Tariff", "Payment", "AuditLog", "SystemSetting"]