from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from backend.app.db.session import Base


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    source_file = Column(String(255), nullable=False, unique=True)
    full_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    location = Column(String(255), nullable=True)
    skills_csv = Column(Text, nullable=True)
    raw_text = Column(Text, nullable=False)
    parsed_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

