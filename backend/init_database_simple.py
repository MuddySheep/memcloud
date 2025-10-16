"""
Simple database initialization script for MemCloud
Creates the basic tables we need for multi-tenant deployment
"""
import asyncio
from app.db.database import init_db, get_engine

async def main():
    """Initialize database with all tables"""
    print("=> Creating database tables...")

    try:
        await init_db()
        print("=> Tables created successfully!")

        # Verify tables exist
        from sqlalchemy import text
        from app.db.database import get_db

        async with get_db() as db:
            result = await db.execute(text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema='public'
                AND table_name IN ('users', 'instances', 'api_keys', 'usage_metrics')
                ORDER BY table_name
            """))
            tables = result.fetchall()

            print("\nCreated tables:")
            for table in tables:
                print(f"  - {table[0]}")

    except Exception as e:
        print(f"ERROR: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
