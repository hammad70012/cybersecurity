from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    func
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Scan(Base):
    __tablename__ = "scans"

    id = Column(Integer, primary_key=True, index=True)
    scanned_at = Column(DateTime(timezone=True), server_default=func.now())
    original_url = Column(String)
    final_url = Column(String)
    is_safe = Column(Boolean)
    risk_score = Column(Integer)
