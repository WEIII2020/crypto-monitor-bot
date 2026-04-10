#!/usr/bin/env python3
"""Initialize PostgreSQL database with schema"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from src.database.models import Base
from src.config import config


def setup_database():
    """Create all tables and indexes"""
    engine = create_engine(config.database_url)

    # Create tables
    Base.metadata.create_all(engine)
    print("✅ Tables created successfully")

    # Create cleanup function
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE OR REPLACE FUNCTION cleanup_old_data()
            RETURNS void AS $$
            BEGIN
                DELETE FROM price_data WHERE timestamp < NOW() - INTERVAL '6 months';
                DELETE FROM alerts WHERE sent_at < NOW() - INTERVAL '6 months';
                DELETE FROM market_maker_analysis WHERE detected_at < NOW() - INTERVAL '6 months';
            END;
            $$ LANGUAGE plpgsql;
        """))
        conn.commit()
        print("✅ Cleanup function created")

    print("\n🎉 Database setup complete!")


if __name__ == '__main__':
    setup_database()
