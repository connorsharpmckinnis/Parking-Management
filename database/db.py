from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Configuration from Environment
# Defaulting to a local postgres if running in podman/network
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/parking_db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
