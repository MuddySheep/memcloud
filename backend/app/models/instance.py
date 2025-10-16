"""
Instance Model - Tracks deployed MemMachine instances on Cloud Run
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, Column, DateTime, String, Integer,
    ForeignKey, Index, Enum as SQLEnum, JSON, text
)
from sqlalchemy.orm import relationship
import enum

from app.db.database import Base


class InstanceStatus(str, enum.Enum):
    """Instance lifecycle status"""
    CREATING = "creating"  # Deployment in progress
    RUNNING = "running"    # Instance is active and healthy
    STOPPED = "stopped"    # Instance is stopped (min instances = 0)
    FAILED = "failed"      # Deployment or health check failed
    DELETING = "deleting"  # Deletion in progress
    DELETED = "deleted"    # Instance has been deleted


class Instance(Base):
    """
    Instance model - represents a deployed MemMachine instance on Cloud Run.

    Each instance is a separate Cloud Run service with its own URL and configuration.

    Relationships:
        - owner: The user who owns this instance
        - api_keys: API keys for accessing this instance
        - metrics: Usage metrics for this instance
    """
    __tablename__ = "instances"

    # Primary Key
    id = Column(
        String(36),
        primary_key=True,
        index=True,
        server_default=text("gen_random_uuid()::text"),
        comment="UUID primary key"
    )

    # Owner
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User who owns this instance"
    )

    # Instance Identity
    name = Column(
        String(255),
        nullable=False,
        comment="Human-readable instance name"
    )

    slug = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="URL-safe slug for the instance (e.g., 'my-memory-1')"
    )

    # Cloud Run Configuration - MemMachine
    cloud_run_service_name = Column(
        String(255),
        unique=True,
        nullable=True,
        comment="Cloud Run service name"
    )

    cloud_run_url = Column(
        String(512),
        nullable=True,
        comment="Public URL of the Cloud Run service"
    )

    region = Column(
        String(50),
        default="us-central1",
        nullable=False,
        comment="GCP region where instance is deployed"
    )

    # Neo4j Configuration
    neo4j_service_name = Column(
        String(255),
        nullable=True,
        comment="Neo4j Cloud Run service name"
    )

    neo4j_url = Column(
        String(512),
        nullable=True,
        comment="Neo4j HTTP URL"
    )

    neo4j_bolt_url = Column(
        String(512),
        nullable=True,
        comment="Neo4j Bolt URL for connections"
    )

    neo4j_secret_name = Column(
        String(255),
        nullable=True,
        comment="Secret Manager name for Neo4j password"
    )

    # PostgreSQL Configuration
    postgres_instance_name = Column(
        String(255),
        nullable=True,
        comment="Cloud SQL PostgreSQL instance name"
    )

    postgres_ip = Column(
        String(50),
        nullable=True,
        comment="PostgreSQL public IP address"
    )

    postgres_connection_name = Column(
        String(512),
        nullable=True,
        comment="Cloud SQL connection name (project:region:instance)"
    )

    postgres_secret_name = Column(
        String(255),
        nullable=True,
        comment="Secret Manager name for PostgreSQL password"
    )

    postgres_database = Column(
        String(100),
        default="memmachine",
        nullable=False,
        comment="PostgreSQL database name"
    )

    postgres_user = Column(
        String(100),
        default="postgres",
        nullable=False,
        comment="PostgreSQL username"
    )

    # OpenAI Configuration
    openai_secret_name = Column(
        String(255),
        nullable=True,
        comment="Secret Manager name for OpenAI API key"
    )

    # Status
    status = Column(
        SQLEnum(InstanceStatus),
        default=InstanceStatus.CREATING,
        nullable=False,
        index=True,
        comment="Current instance status"
    )

    health_status = Column(
        String(50),
        default="unknown",
        nullable=False,
        comment="Health check status (healthy, unhealthy, unknown)"
    )

    last_health_check = Column(
        DateTime,
        nullable=True,
        comment="Last health check timestamp"
    )

    # Configuration
    config = Column(
        JSON,
        default={},
        nullable=False,
        comment="Instance configuration (memory size, CPU, etc.)"
    )

    # Resource Limits
    memory_mb = Column(
        Integer,
        default=512,
        nullable=False,
        comment="Memory allocation in MB"
    )

    cpu_count = Column(
        Integer,
        default=1,
        nullable=False,
        comment="CPU count"
    )

    min_instances = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Minimum number of instances (0 = scale to zero)"
    )

    max_instances = Column(
        Integer,
        default=10,
        nullable=False,
        comment="Maximum number of instances"
    )

    # Metadata
    description = Column(
        String(1000),
        nullable=True,
        comment="Instance description"
    )

    tags = Column(
        JSON,
        default=[],
        nullable=False,
        comment="User-defined tags"
    )

    # Timestamps
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
        comment="Instance creation timestamp"
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        comment="Last update timestamp"
    )

    deployed_at = Column(
        DateTime,
        nullable=True,
        comment="Successful deployment timestamp"
    )

    deleted_at = Column(
        DateTime,
        nullable=True,
        comment="Deletion timestamp (soft delete)"
    )

    # Deployment Info
    deployment_error = Column(
        String(2000),
        nullable=True,
        comment="Error message if deployment failed"
    )

    deployment_logs_url = Column(
        String(512),
        nullable=True,
        comment="URL to Cloud Run deployment logs"
    )

    # Relationships
    owner = relationship(
        "User",
        back_populates="instances"
    )

    api_keys = relationship(
        "APIKey",
        back_populates="instance",
        cascade="all, delete-orphan"
    )

    metrics = relationship(
        "UsageMetric",
        back_populates="instance",
        cascade="all, delete-orphan"
    )

    # Indexes for performance
    __table_args__ = (
        Index('ix_instances_user_status', 'user_id', 'status'),
        Index('ix_instances_slug', 'slug'),
        Index('ix_instances_cloud_run_service', 'cloud_run_service_name'),
    )

    def __repr__(self) -> str:
        return f"<Instance(id={self.id}, name={self.name}, status={self.status})>"

    @property
    def is_healthy(self) -> bool:
        """Check if instance is healthy and running"""
        return (
            self.status == InstanceStatus.RUNNING and
            self.health_status == "healthy"
        )

    @property
    def is_deployable(self) -> bool:
        """Check if instance can be deployed"""
        return self.status in [
            InstanceStatus.CREATING,
            InstanceStatus.STOPPED,
            InstanceStatus.FAILED
        ]
