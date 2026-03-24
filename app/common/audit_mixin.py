# app/common/audit_mixin.py
from sqlalchemy import DateTime, Integer, ForeignKey
from sqlalchemy.orm import declarative_mixin, declared_attr, Mapped, mapped_column
from datetime import datetime, timezone
from typing import Optional


@declarative_mixin
class TimestampMixin:
    """Basic timestamp audit fields."""
    
    @declared_attr
    def created_at(cls) -> Mapped[datetime]:
        return mapped_column(
            DateTime(timezone=True),
            default=lambda: datetime.now(timezone.utc),
            nullable=False
        )

    @declared_attr
    def updated_at(cls) -> Mapped[datetime]:
        return mapped_column(
            DateTime(timezone=True),
            default=lambda: datetime.now(timezone.utc),
            onupdate=lambda: datetime.now(timezone.utc),
            nullable=False
        )


@declarative_mixin 
class UserAuditMixin:
    """User reference audit fields."""
    
    @declared_attr
    def created_by_id(cls) -> Mapped[Optional[int]]:
        return mapped_column(
            Integer,
            ForeignKey("users.id", ondelete="SET NULL"), 
            nullable=True,
            index=True
        )
    
    @declared_attr
    def updated_by_id(cls) -> Mapped[Optional[int]]:
        return mapped_column(
            Integer,
            ForeignKey("users.id", ondelete="SET NULL"), 
            nullable=True,
            index=True
        )

@declarative_mixin
class SoftDeleteMixin:
    """Soft delete functionality."""
    
    @declared_attr
    def deleted_at(cls) -> Mapped[Optional[datetime]]:
        return mapped_column(DateTime(timezone=True), nullable=True)
    
    @declared_attr
    def deleted_by_id(cls) -> Mapped[Optional[int]]:
        return mapped_column(
            Integer, 
            ForeignKey("users.id", ondelete="SET NULL"), 
            nullable=True,
        )

# Convenience combination for common usage
@declarative_mixin
class FullAuditMixin(TimestampMixin, UserAuditMixin, SoftDeleteMixin):
    """Complete audit trail with all features."""
    pass
