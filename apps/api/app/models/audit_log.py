"""Append-only audit records for attributable admin activity."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, Text, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import APPLICATION_SCHEMA
from app.models.base import Base

type JSONScalar = str | int | float | bool | None
type JSONValue = JSONScalar | list[JSONValue] | dict[str, JSONValue]


class AuditLog(Base):
    """One redacted, backend-only audit event staged with its owning transaction."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        CheckConstraint(
            "char_length(btrim(action)) BETWEEN 1 AND 100",
            name="ck_audit_logs_action_length",
        ),
        CheckConstraint(
            "char_length(btrim(resource_type)) BETWEEN 1 AND 100",
            name="ck_audit_logs_resource_type_length",
        ),
        Index("ix_audit_logs_admin_id_created_at", "admin_id", "created_at"),
        Index(
            "ix_audit_logs_resource_type_resource_id",
            "resource_type",
            "resource_id",
        ),
    )

    admin_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(f"{APPLICATION_SCHEMA}.users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(Text, nullable=False)
    resource_type: Mapped[str] = mapped_column(Text, nullable=False)
    resource_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    old_value: Mapped[dict[str, JSONValue] | None] = mapped_column(JSONB, nullable=True)
    new_value: Mapped[dict[str, JSONValue] | None] = mapped_column(JSONB, nullable=True)
    context: Mapped[dict[str, JSONValue]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
