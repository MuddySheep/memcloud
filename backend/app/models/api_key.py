"""
API Key Model - For authenticating access to MemMachine instances
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, Column, DateTime, String, Integer,
    ForeignKey, Index, text
)
from sqlalchemy.orm import relationship

from app.db.database import Base


class APIKey(Base):
    """
    API Key model - represents an API key for accessing a MemMachine instance.

    Each instance can have multiple API keys for different use cases
    (e.g., production, development, readonly).

    PFF Security Gate:
    - ✅ Keys are hashed before storage
    - ✅ Rate limiting per key
    - ✅ Expiration dates enforced
    - ✅ Audit trail of key usage
    """
    __tablename__ = "api_keys"

    # Primary Key
    id = Column(
        String(36),
        primary_key=True,
        index=True,
        server_default=text("gen_random_uuid()::text"),
        comment="UUID primary key"
    )

    # Ownership
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User who created this API key"
    )

    instance_id = Column(
        String(36),
        ForeignKey("instances.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Instance this key provides access to"
    )

    # Key Information
    name = Column(
        String(255),
        nullable=False,
        comment="Human-readable key name (e.g., 'Production Key')"
    )

    key_prefix = Column(
        String(10),
        nullable=False,
        index=True,
        comment="First 8 characters of the key for identification"
    )

    key_hash = Column(
        String(255),
        unique=True,
        nullable=False,
        comment="Hashed API key (never store plaintext!)"
    )

    # Permissions
    is_readonly = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether key can only read, not write"
    )

    # Status
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether key is currently active"
    )

    # Rate Limiting
    rate_limit_per_minute = Column(
        Integer,
        default=60,
        nullable=False,
        comment="Maximum requests per minute"
    )

    # Usage Tracking
    last_used_at = Column(
        DateTime,
        nullable=True,
        comment="Last time this key was used"
    )

    usage_count = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Total number of requests made with this key"
    )

    # Expiration
    expires_at = Column(
        DateTime,
        nullable=True,
        comment="Key expiration date (null = never expires)"
    )

    # Timestamps
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
        comment="Key creation timestamp"
    )

    revoked_at = Column(
        DateTime,
        nullable=True,
        comment="When key was revoked (null = not revoked)"
    )

    # Relationships
    user = relationship(
        "User",
        back_populates="api_keys"
    )

    instance = relationship(
        "Instance",
        back_populates="api_keys"
    )

    # Indexes for performance
    __table_args__ = (
        Index('ix_api_keys_user_instance', 'user_id', 'instance_id'),
        Index('ix_api_keys_key_hash', 'key_hash'),
        Index('ix_api_keys_prefix_active', 'key_prefix', 'is_active'),
    )

    def __repr__(self) -> str:
        return f"<APIKey(id={self.id}, name={self.name}, prefix={self.key_prefix})>"

    @property
    def is_valid(self) -> bool:
        """Check if key is valid for use"""
        if not self.is_active:
            return False

        if self.revoked_at is not None:
            return False

        if self.expires_at is not None and self.expires_at < datetime.utcnow():
            return False

        return True

    @property
    def display_key(self) -> str:
        """Get display-safe key (prefix + asterisks)"""
        return f"{self.key_prefix}{'*' * 32}"
