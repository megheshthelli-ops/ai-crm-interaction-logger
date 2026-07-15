from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db, seed_sample_data
from app.routers import interactions, extraction
from app.settings import settings

# Initialize database and seed sample data
init_db()
try:
    seed_sample_data()
except Exception as e:
    print(f"Warning: sample data seed failed: {e}")

# Create FastAPI app
app = FastAPI(
    title="AI-First CRM HCP Module",
    description="Healthcare Professional Customer Relationship Management System",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "message": "AI-First CRM HCP Module API is running",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


# Include routers
app.include_router(interactions.router)
app.include_router(extraction.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )