from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, projects, files, analysis, report

app = FastAPI(
    title="LabelIQ API",
    description="Backend API for CFIA Food Labelling Analysis",
    version="1.0.0"
)

# Configure CORS for frontend - allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # Must be False when using wildcard origins
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(files.router)
app.include_router(analysis.router)
app.include_router(report.router)


@app.get("/")
async def root():
    return {"message": "LabelIQ API is running", "docs": "/docs"}


@app.get("/api/health")
async def health():
    return {"status": "healthy"}
