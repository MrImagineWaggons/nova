from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    discord_id = Column(String, unique=True, index=True)
    username = Column(String)

    plan_type = Column(String, nullable=True)
    expires_at = Column(DateTime, nullable=True)


class LicenseKey(Base):
    __tablename__ = "license_keys"

    id = Column(Integer, primary_key=True, index=True)
    key_value = Column(String, unique=True, index=True)
    plan_type = Column(String)
    duration_days = Column(Integer)
    bound_discord_id = Column(String, nullable=True)
