from sqlalchemy import Column, String, Text, DateTime, Enum, JSON, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone
import uuid
import enum

Base = declarative_base()


class Severity(str, enum.Enum):
    info = "info"
    warning = "warning"
    error = "error"
    critical = "critical"


class Event(Base):
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    severity = Column(Enum(Severity), nullable=False, index=True)
    service = Column(String(255), nullable=False, index=True)
    message = Column(Text, nullable=False)
    stack_trace = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True, default=dict)
    environment = Column(String(64), nullable=True, default="production", index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)

    __table_args__ = (
        Index("ix_events_timestamp", "timestamp"),
        Index("ix_events_severity_timestamp", "severity", "timestamp"),
        Index("ix_events_service_timestamp", "service", "timestamp"),
    )
