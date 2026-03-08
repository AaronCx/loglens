"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-03-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "severity",
            sa.Enum("info", "warning", "error", "critical", name="severity"),
            nullable=False,
        ),
        sa.Column("service", sa.String(255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("stack_trace", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("environment", sa.String(64), nullable=True, server_default="production"),
    )
    op.create_index("ix_events_severity", "events", ["severity"])
    op.create_index("ix_events_service", "events", ["service"])
    op.create_index("ix_events_environment", "events", ["environment"])
    op.create_index("ix_events_timestamp", "events", ["timestamp"])
    op.create_index("ix_events_severity_timestamp", "events", ["severity", "timestamp"])
    op.create_index("ix_events_service_timestamp", "events", ["service", "timestamp"])


def downgrade() -> None:
    op.drop_index("ix_events_service_timestamp")
    op.drop_index("ix_events_severity_timestamp")
    op.drop_index("ix_events_timestamp")
    op.drop_index("ix_events_environment")
    op.drop_index("ix_events_service")
    op.drop_index("ix_events_severity")
    op.drop_table("events")
    op.execute("DROP TYPE IF EXISTS severity")
