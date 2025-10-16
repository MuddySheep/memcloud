"""
Database Migration Runner for MemCloud

Run this script to apply all pending database migrations.

Usage:
    python migrate.py upgrade      # Apply all pending migrations
    python migrate.py downgrade    # Rollback one migration
    python migrate.py current      # Show current revision
    python migrate.py history      # Show migration history
"""
import sys
import asyncio
from alembic.config import Config
from alembic import command


def get_alembic_config():
    """Get Alembic configuration"""
    alembic_cfg = Config("alembic.ini")
    return alembic_cfg


def upgrade():
    """Apply all pending migrations"""
    print("=> Applying database migrations...")
    alembic_cfg = get_alembic_config()
    command.upgrade(alembic_cfg, "head")
    print("=> Migrations applied successfully!")


def downgrade():
    """Rollback one migration"""
    print("=> Rolling back last migration...")
    alembic_cfg = get_alembic_config()
    command.downgrade(alembic_cfg, "-1")
    print("=> Rollback complete!")


def current():
    """Show current database revision"""
    print("=> Current database revision:")
    alembic_cfg = get_alembic_config()
    command.current(alembic_cfg)


def history():
    """Show migration history"""
    print("=> Migration history:")
    alembic_cfg = get_alembic_config()
    command.history(alembic_cfg)


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    action = sys.argv[1]

    actions = {
        "upgrade": upgrade,
        "downgrade": downgrade,
        "current": current,
        "history": history,
    }

    if action not in actions:
        print(f"ERROR: Unknown action: {action}")
        print(__doc__)
        sys.exit(1)

    try:
        actions[action]()
    except Exception as e:
        print(f"ERROR: Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
