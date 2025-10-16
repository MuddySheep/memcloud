"""add multi-tenant resource tracking

Revision ID: 001_multi_tenant
Revises:
Create Date: 2025-10-14 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_multi_tenant'
down_revision = '000_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add multi-tenant resource tracking fields to instances table.

    These fields enable tracking of per-user isolated resources:
    - Neo4j Cloud Run services
    - Cloud SQL PostgreSQL instances
    - Secret Manager secrets
    """
    # Neo4j Configuration
    op.add_column('instances', sa.Column('neo4j_service_name', sa.String(length=255), nullable=True, comment='Neo4j Cloud Run service name'))
    op.add_column('instances', sa.Column('neo4j_url', sa.String(length=512), nullable=True, comment='Neo4j HTTP URL'))
    op.add_column('instances', sa.Column('neo4j_bolt_url', sa.String(length=512), nullable=True, comment='Neo4j Bolt URL for connections'))
    op.add_column('instances', sa.Column('neo4j_secret_name', sa.String(length=255), nullable=True, comment='Secret Manager name for Neo4j password'))

    # PostgreSQL Configuration
    op.add_column('instances', sa.Column('postgres_instance_name', sa.String(length=255), nullable=True, comment='Cloud SQL PostgreSQL instance name'))
    op.add_column('instances', sa.Column('postgres_ip', sa.String(length=50), nullable=True, comment='PostgreSQL public IP address'))
    op.add_column('instances', sa.Column('postgres_connection_name', sa.String(length=512), nullable=True, comment='Cloud SQL connection name (project:region:instance)'))
    op.add_column('instances', sa.Column('postgres_secret_name', sa.String(length=255), nullable=True, comment='Secret Manager name for PostgreSQL password'))
    op.add_column('instances', sa.Column('postgres_database', sa.String(length=100), nullable=False, server_default='memmachine', comment='PostgreSQL database name'))
    op.add_column('instances', sa.Column('postgres_user', sa.String(length=100), nullable=False, server_default='postgres', comment='PostgreSQL username'))

    # OpenAI Configuration
    op.add_column('instances', sa.Column('openai_secret_name', sa.String(length=255), nullable=True, comment='Secret Manager name for OpenAI API key'))


def downgrade() -> None:
    """Remove multi-tenant resource tracking fields."""
    # Remove in reverse order
    op.drop_column('instances', 'openai_secret_name')
    op.drop_column('instances', 'postgres_user')
    op.drop_column('instances', 'postgres_database')
    op.drop_column('instances', 'postgres_secret_name')
    op.drop_column('instances', 'postgres_connection_name')
    op.drop_column('instances', 'postgres_ip')
    op.drop_column('instances', 'postgres_instance_name')
    op.drop_column('instances', 'neo4j_secret_name')
    op.drop_column('instances', 'neo4j_bolt_url')
    op.drop_column('instances', 'neo4j_url')
    op.drop_column('instances', 'neo4j_service_name')
