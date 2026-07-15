"""
Sample data initialization script for testing
Run this after setting up the database to populate sample HCPs and materials
"""

from app.database import SessionLocal
from app.models import HCP, Material
from datetime import datetime

def init_sample_data():
    db = SessionLocal()
    
    try:
        # Check if data already exists
        existing_hcps = db.query(HCP).count()
        if existing_hcps > 0:
            print("Sample data already exists. Skipping...")
            return
        
        # Sample HCPs
        hcps = [
            HCP(
                name="Dr. John Smith",
                specialty="Cardiology",
                organization="City Medical Center",
                email="john.smith@citymed.com",
                phone="+1-555-0101"
            ),
            HCP(
                name="Dr. Jane Doe",
                specialty="Neurology",
                organization="State Hospital",
                email="jane.doe@statehospital.com",
                phone="+1-555-0102"
            ),
            HCP(
                name="Dr. Robert Johnson",
                specialty="Oncology",
                organization="Research Institute",
                email="robert.johnson@research.com",
                phone="+1-555-0103"
            ),
            HCP(
                name="Dr. Sarah Williams",
                specialty="Rheumatology",
                organization="Metro Clinic",
                email="sarah.williams@metroc.com",
                phone="+1-555-0104"
            ),
            HCP(
                name="Dr. Michael Brown",
                specialty="Gastroenterology",
                organization="Digestive Health Center",
                email="m.brown@digesthealth.com",
                phone="+1-555-0105"
            ),
        ]
        
        db.add_all(hcps)
        db.commit()
        print(f"✅ Added {len(hcps)} sample HCPs")
        
        # Sample Materials
        materials = [
            Material(
                name="Cardiac Care Guidelines 2024",
                category="Cardiology",
                description="Latest guidelines for cardiac disease management"
            ),
            Material(
                name="Neurological Disorders Overview",
                category="Neurology",
                description="Comprehensive overview of common neurological conditions"
            ),
            Material(
                name="Cancer Treatment Protocols",
                category="Oncology",
                description="Evidence-based cancer treatment protocols"
            ),
            Material(
                name="Rheumatoid Arthritis Management",
                category="Rheumatology",
                description="Best practices for RA management and patient care"
            ),
            Material(
                name="GI Health Reference",
                category="Gastroenterology",
                description="Reference guide for gastrointestinal health management"
            ),
            Material(
                name="Clinical Trial Information",
                category="General",
                description="Overview of ongoing clinical trials"
            ),
        ]
        
        db.add_all(materials)
        db.commit()
        print(f"✅ Added {len(materials)} sample materials")
        
        print("\n✅ Sample data initialized successfully!")
        print("\nYou can now:")
        print("1. Login and select HCPs from the form")
        print("2. Log interactions for these HCPs")
        print("3. View interaction history")
        print("4. Get material recommendations based on topics")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error initializing sample data: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    init_sample_data()
