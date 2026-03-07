from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool, StaticPool
from app.config import settings

# Create database engine
# Use StaticPool for SQLite to avoid threading issues
if settings.DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=settings.DEBUG,
    )
else:
    # PostgreSQL or other databases
    engine = create_engine(
        settings.DATABASE_URL,
        poolclass=NullPool,
        echo=settings.DEBUG,
    )

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Declarative base for ORM models
Base = declarative_base()


def get_db():
    """Dependency for FastAPI to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all_tables():
    """Create all tables in the database."""
    Base.metadata.create_all(bind=engine)


def drop_all_tables():
    """Drop all tables from the database (WARNING: Destructive)."""
    Base.metadata.drop_all(bind=engine)
