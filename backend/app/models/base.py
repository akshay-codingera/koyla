import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime
from app.db.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class UUIDMixin:
    id = Column(String(36), primary_key=True, default=generate_uuid)
    created_at = Column(DateTime, default=datetime.utcnow)
