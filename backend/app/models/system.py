from sqlalchemy import Column, String, JSON, DateTime
from datetime import datetime
from app.db.database import Base

class SystemSettings(Base):
    __tablename__ = "system_settings"
    key = Column(String(100), primary_key=True)
    value = Column(JSON, default={})
    description = Column(String(255))
    updated_at = Column(DateTime, default=datetime.utcnow)
