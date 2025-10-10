"""
Usage Metric Model - Tracks usage statistics for instances
"""
from datetime import datetime

from sqlalchemy import (
    Column, DateTime, String, Integer, Float,
    ForeignKey, Index, text
)
from sqlalchemy.orm import relationship

from app.db.database import Base


class UsageMetric(Base):
    """
    Usage Metric model - tracks usage statistics for MemMachine instances.

    Used for billing, analytics, and capacity planning.

    Metrics tracked:
    - Request counts
    - Memory operations (add, query, search)
    - Response times
    - Error rates
    - Data volume
    """
    __tablename__ = "usage_metrics"

    # Primary Key
    id = Column(
        String(36),
        primary_key=True,
        index=True,
        server_default=text("gen_random_uuid()::text"),
        comment="UUID primary key"
    )

    # Foreign Keys
    instance_id = Column(
        String(36),
        ForeignKey("instances.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Instance these metrics belong to"
    )

    # Time Period (for aggregation)
    period_start = Column(
        DateTime,
        nullable=False,
        index=True,
        comment="Start of the measurement period"
    )

    period_end = Column(
        DateTime,
        nullable=False,
        comment="End of the measurement period"
    )

    # Request Metrics
    total_requests = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Total number of requests in this period"
    )

    successful_requests = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of successful requests (2xx status)"
    )

    failed_requests = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of failed requests (4xx, 5xx status)"
    )

    # Operation Breakdown
    add_operations = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of memory add operations"
    )

    query_operations = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of memory query operations"
    )

    search_operations = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of memory search operations"
    )

    delete_operations = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of memory delete operations"
    )

    # Performance Metrics
    avg_response_time_ms = Column(
        Float,
        default=0.0,
        nullable=False,
        comment="Average response time in milliseconds"
    )

    p95_response_time_ms = Column(
        Float,
        default=0.0,
        nullable=False,
        comment="95th percentile response time in milliseconds"
    )

    p99_response_time_ms = Column(
        Float,
        default=0.0,
        nullable=False,
        comment="99th percentile response time in milliseconds"
    )

    # Data Volume
    data_stored_mb = Column(
        Float,
        default=0.0,
        nullable=False,
        comment="Total data stored in megabytes"
    )

    data_transferred_mb = Column(
        Float,
        default=0.0,
        nullable=False,
        comment="Total data transferred in megabytes"
    )

    # Cost Estimation (calculated from usage)
    estimated_cost_usd = Column(
        Float,
        default=0.0,
        nullable=False,
        comment="Estimated cost in USD for this period"
    )

    # Timestamps
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        comment="Metric creation timestamp"
    )

    # Relationships
    instance = relationship(
        "Instance",
        back_populates="metrics"
    )

    # Indexes for performance
    __table_args__ = (
        Index('ix_metrics_instance_period', 'instance_id', 'period_start', 'period_end'),
        Index('ix_metrics_period_start', 'period_start'),
    )

    def __repr__(self) -> str:
        return (
            f"<UsageMetric(instance_id={self.instance_id}, "
            f"period={self.period_start} to {self.period_end}, "
            f"requests={self.total_requests})>"
        )

    @property
    def error_rate(self) -> float:
        """Calculate error rate as percentage"""
        if self.total_requests == 0:
            return 0.0
        return (self.failed_requests / self.total_requests) * 100

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage"""
        if self.total_requests == 0:
            return 100.0
        return (self.successful_requests / self.total_requests) * 100
