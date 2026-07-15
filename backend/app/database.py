from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.settings import settings

DATABASE_URL = settings.database_url

# Create engine
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False,
    )
else:
    engine = create_engine(
        DATABASE_URL,
        poolclass=NullPool,
        echo=False,
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


import logging

logger = logging.getLogger(__name__)


def seed_sample_data():
    """Populate sample HCP and material data when the database is empty."""
    from .models import HCP, Material

    db = SessionLocal()
    try:
        existing_hcps = db.query(HCP).count()
        if existing_hcps > 0:
            logger.info("Sample data already exists. Skipping seed.")
            return

        hcps = [
            HCP(name="Dr. John Smith", specialty="Cardiology", organization="City Medical Center",
                email="john.smith@citymed.com", phone="+1-555-0101"),
            HCP(name="Dr. Jane Doe", specialty="Neurology", organization="State Hospital",
                email="jane.doe@statehospital.com", phone="+1-555-0102"),
            HCP(name="Dr. Robert Johnson", specialty="Oncology", organization="Research Institute",
                email="robert.johnson@research.com", phone="+1-555-0103"),
            HCP(name="Dr. Sarah Williams", specialty="Rheumatology", organization="Metro Clinic",
                email="sarah.williams@metroc.com", phone="+1-555-0104"),
            HCP(name="Dr. Michael Brown", specialty="Gastroenterology", organization="Digestive Health Center",
                email="m.brown@digesthealth.com", phone="+1-555-0105"),
        ]
        db.add_all(hcps)

        materials = [
            Material(name="Cardiac Care Guidelines 2024", category="Cardiology",
                     description="Latest guidelines for cardiac disease management"),
            Material(name="Neurological Disorders Overview", category="Neurology",
                     description="Comprehensive overview of common neurological conditions"),
            Material(name="Cancer Treatment Protocols", category="Oncology",
                     description="Evidence-based cancer treatment protocols"),
            Material(name="Rheumatoid Arthritis Management", category="Rheumatology",
                     description="Best practices for RA management and patient care"),
            Material(name="GI Health Reference", category="Gastroenterology",
                     description="Reference guide for gastrointestinal health management"),
            Material(name="Clinical Trial Information", category="General",
                     description="Overview of ongoing clinical trials"),
        ]
        db.add_all(materials)
        db.commit()
        logger.info(f"Seeded {len(hcps)} HCPs and {len(materials)} materials")
    except Exception as e:
        db.rollback()
        logger.error(f"Seed failed: {e}")
        raise
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    from .models import Base
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized")
