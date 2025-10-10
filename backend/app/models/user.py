"""
User Model - Production Forcing Framework Compliant

PFF Gates:
- ✅ Proper types (no 'any')
- ✅ Indexed fields for performance
- ✅ Timestamps for auditing
- ✅ Relationships properly defined
"""
from datetime import datetime
from typing import List

from sqlalchemy import Boolean, Column, DateTime, String, Index, text
from sqlalchemy.orm import relationship

from app.db.database import Base


class User(Base):
    """
    User model - represents a user of the MemCloud platform.

    Linked to Firebase Auth via firebase_uid.

    Relationships:
        - instances: List of MemMachine instances owned by this user
        - api_keys: List of API keys created by this user
    """
    __tablename__ = "users"

    # Primary Key
    id = Column(
        String(36),
        primary_key=True,
        index=True,
        server_default=text("gen_random_uuid()::text"),
        comment="UUID primary key"
    )

    # Firebase Auth Integration
    firebase_uid = Column(
        String(128),
        unique=True,
        nullable=False,
        index=True,
        comment="Firebase Authentication UID"
    )

    # User Information
    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="User email address"
    )

    display_name = Column(
        String(255),
        nullable=True,
        comment="User display name"
    )

    # Status
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether user account is active"
    )

    is_verified = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether user email is verified"
    )

    # Timestamps
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
        comment="Account creation timestamp"
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        comment="Last update timestamp"
    )

    last_login_at = Column(
        DateTime,
        nullable=True,
        comment="Last login timestamp"
    )

    # Relationships
    instances = relationship(
        "Instance",
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    api_keys = relationship(
        "APIKey",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    # Indexes for performance
    __table_args__ = (
        Index('ix_users_email_active', 'email', 'is_active'),
        Index('ix_users_firebase_uid', 'firebase_uid'),
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"
