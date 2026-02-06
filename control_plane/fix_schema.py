import os
import sys
from sqlalchemy import create_engine, text

# Setup path to import from parent directory if needed, 
# though we are just using raw SQL mostly.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:password@db:5432/parking_db")
engine = create_engine(DATABASE_URL)

def run_migration():
    with engine.connect() as conn:
        # necessary for some DDL statements in some drivers, though usually ok in block
        conn = conn.execution_options(isolation_level="AUTOCOMMIT")
        
        print("Starting schema migration...")
        
        # 1. Create Enum Type connectiontype
        try:
            # PostgreSQL specific block to create type safely
            conn.execute(text("""
            DO $$ 
            BEGIN 
                CREATE TYPE connectiontype AS ENUM ('FIBER', 'EDGE', 'fiber', 'edge'); 
            EXCEPTION 
                WHEN duplicate_object THEN null; 
            END $$;
            """))
            print("Checked/Created connectiontype Enum")
        except Exception as e:
            print(f"Enum creation note: {e}")

        # 2. Add connection_type column
        try:
            conn.execute(text("ALTER TABLE cameras ADD COLUMN IF NOT EXISTS connection_type connectiontype DEFAULT 'FIBER'"))
            print("Added connection_type column")
        except Exception as e:
            print(f"Error adding connection_type: {e}")

        # 3. Add occupancy_bottom_pct
        try:
            conn.execute(text("ALTER TABLE cameras ADD COLUMN IF NOT EXISTS occupancy_bottom_pct FLOAT DEFAULT 0.33"))
            print("Added occupancy_bottom_pct column")
        except Exception as e:
            print(f"Error adding occupancy_bottom_pct: {e}")

        # 4. Add occupancy_min_overlap
        try:
            conn.execute(text("ALTER TABLE cameras ADD COLUMN IF NOT EXISTS occupancy_min_overlap FLOAT DEFAULT 0.30"))
            print("Added occupancy_min_overlap column")
        except Exception as e:
            print(f"Error adding occupancy_min_overlap: {e}")

        # 5. Add stream_url (in case it's missing)
        try:
            conn.execute(text("ALTER TABLE cameras ADD COLUMN IF NOT EXISTS stream_url VARCHAR"))
            print("Added stream_url column")
        except Exception as e:
             print(f"Error adding stream_url: {e}")

        # 6. Add is_deleted (for soft delete)
        try:
            conn.execute(text("ALTER TABLE cameras ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE"))
            print("Added is_deleted column")
        except Exception as e:
             print(f"Error adding is_deleted: {e}")

        print("Migration complete.")

if __name__ == "__main__":
    run_migration()
