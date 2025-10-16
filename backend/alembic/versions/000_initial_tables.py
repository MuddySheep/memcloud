"""initial tables

Revision ID: 000_initial
Revises:
Create Date: 2025-10-14 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '000_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial database tables for MemCloud multi-tenant architecture."""

    # Create users table
    op.create_table('users',
        sa.Column('id', sa.String(length=36), server_default=sa.text("gen_random_uuid()::text"), nullable=False, comment='UUID primary key'),
        sa.Column('firebase_uid', sa.String(length=128), nullable=False, comment='Firebase Authentication UID'),
        sa.Column('email', sa.String(length=255), nullable=False, comment='User email address'),
        sa.Column('display_name', sa.String(length=255), nullable=True, comment='User display name'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true'), comment='Whether user account is active'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.text('false'), comment='Whether user email is verified'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'), comment='Account creation timestamp'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'), comment='Last update timestamp'),
        sa.Column('last_login_at', sa.DateTime(), nullable=True, comment='Last login timestamp'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_email_active', 'users', ['email', 'is_active'])
    op.create_index('ix_users_firebase_uid', 'users', ['firebase_uid'])
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index(op.f('ix_users_created_at'), 'users', ['created_at'])
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_firebase_uid'), 'users', ['firebase_uid'], unique=True)

    # Create instances table
    op.create_table('instances',
        sa.Column('id', sa.String(length=36), server_default=sa.text("gen_random_uuid()::text"), nullable=False, comment='UUID primary key'),
        sa.Column('user_id', sa.String(length=36), nullable=False, comment='User who owns this instance'),
        sa.Column('name', sa.String(length=255), nullable=False, comment='Human-readable instance name'),
        sa.Column('slug', sa.String(length=255), nullable=False, comment="URL-safe slug for the instance (e.g., 'my-memory-1')"),
        sa.Column('cloud_run_service_name', sa.String(length=255), nullable=True, comment='Cloud Run service name'),
        sa.Column('cloud_run_url', sa.String(length=512), nullable=True, comment='Public URL of the Cloud Run service'),
        sa.Column('region', sa.String(length=50), nullable=False, server_default='us-central1', comment='GCP region where instance is deployed'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='creating', comment='Current instance status'),
        sa.Column('health_status', sa.String(length=50), nullable=False, server_default='unknown', comment='Health check status (healthy, unhealthy, unknown)'),
        sa.Column('last_health_check', sa.DateTime(), nullable=True, comment='Last health check timestamp'),
        sa.Column('config', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='{}', comment='Instance configuration (memory size, CPU, etc.)'),
        sa.Column('memory_mb', sa.Integer(), nullable=False, server_default='512', comment='Memory allocation in MB'),
        sa.Column('cpu_count', sa.Integer(), nullable=False, server_default='1', comment='CPU count'),
        sa.Column('min_instances', sa.Integer(), nullable=False, server_default='0', comment='Minimum number of instances (0 = scale to zero)'),
        sa.Column('max_instances', sa.Integer(), nullable=False, server_default='10', comment='Maximum number of instances'),
        sa.Column('description', sa.String(length=1000), nullable=True, comment='Instance description'),
        sa.Column('tags', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='[]', comment='User-defined tags'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'), comment='Instance creation timestamp'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'), comment='Last update timestamp'),
        sa.Column('deployed_at', sa.DateTime(), nullable=True, comment='Successful deployment timestamp'),
        sa.Column('deleted_at', sa.DateTime(), nullable=True, comment='Deletion timestamp (soft delete)'),
        sa.Column('deployment_error', sa.String(length=2000), nullable=True, comment='Error message if deployment failed'),
        sa.Column('deployment_logs_url', sa.String(length=512), nullable=True, comment='URL to Cloud Run deployment logs'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_instances_cloud_run_service', 'instances', ['cloud_run_service_name'])
    op.create_index('ix_instances_slug', 'instances', ['slug'])
    op.create_index('ix_instances_user_status', 'instances', ['user_id', 'status'])
    op.create_index('ix_instances_id', 'instances', ['id'])
    op.create_index('ix_instances_user_id', 'instances', ['user_id'])
    op.create_index(op.f('ix_instances_cloud_run_service_name'), 'instances', ['cloud_run_service_name'], unique=True)
    op.create_index(op.f('ix_instances_created_at'), 'instances', ['created_at'])
    op.create_index(op.f('ix_instances_slug'), 'instances', ['slug'], unique=True)
    op.create_index(op.f('ix_instances_status'), 'instances', ['status'])

    # Create api_keys table
    op.create_table('api_keys',
        sa.Column('id', sa.String(length=36), server_default=sa.text("gen_random_uuid()::text"), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('instance_id', sa.String(length=36), nullable=True),
        sa.Column('key_hash', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['instance_id'], ['instances.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_api_keys_id'), 'api_keys', ['id'])
    op.create_index(op.f('ix_api_keys_key_hash'), 'api_keys', ['key_hash'], unique=True)

    # Create usage_metrics table
    op.create_table('usage_metrics',
        sa.Column('id', sa.String(length=36), server_default=sa.text("gen_random_uuid()::text"), nullable=False),
        sa.Column('instance_id', sa.String(length=36), nullable=False),
        sa.Column('metric_type', sa.String(length=50), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['instance_id'], ['instances.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_usage_metrics_id'), 'usage_metrics', ['id'])
    op.create_index(op.f('ix_usage_metrics_timestamp'), 'usage_metrics', ['timestamp'])


def downgrade() -> None:
    """Drop all MemCloud tables."""
    op.drop_index(op.f('ix_usage_metrics_timestamp'), table_name='usage_metrics')
    op.drop_index(op.f('ix_usage_metrics_id'), table_name='usage_metrics')
    op.drop_table('usage_metrics')

    op.drop_index(op.f('ix_api_keys_key_hash'), table_name='api_keys')
    op.drop_index(op.f('ix_api_keys_id'), table_name='api_keys')
    op.drop_table('api_keys')

    op.drop_index(op.f('ix_instances_status'), table_name='instances')
    op.drop_index(op.f('ix_instances_created_at'), table_name='instances')
    op.drop_index(op.f('ix_instances_slug'), table_name='instances')
    op.drop_index(op.f('ix_instances_cloud_run_service_name'), table_name='instances')
    op.drop_index('ix_instances_user_id', table_name='instances')
    op.drop_index('ix_instances_id', table_name='instances')
    op.drop_index('ix_instances_user_status', table_name='instances')
    op.drop_index('ix_instances_slug', table_name='instances')
    op.drop_index('ix_instances_cloud_run_service', table_name='instances')
    op.drop_table('instances')

    op.drop_index(op.f('ix_users_firebase_uid'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_created_at'), table_name='users')
    op.drop_index('ix_users_id', table_name='users')
    op.drop_index('ix_users_firebase_uid', table_name='users')
    op.drop_index('ix_users_email_active', table_name='users')
    op.drop_table('users')
