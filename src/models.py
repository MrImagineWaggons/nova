from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, Float, ForeignKey
from sqlalchemy.sql import func
from db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    discord_id = Column(String, unique=True, index=True, nullable=False)
    username = Column(String)
    plan_type = Column(String, default="free")
    expires_at = Column(TIMESTAMP)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now())


class LicenseKey(Base):
    __tablename__ = "license_keys"

    id = Column(Integer, primary_key=True, index=True)
    key_value = Column(String, unique=True, nullable=False)
    plan_type = Column(String, nullable=False)
    duration_days = Column(Integer, nullable=False)
    used_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(TIMESTAMP, server_default=func.now())
