from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

@app.on_event("startup")
async def startup_event():
    print("🚀 Application started successfully!")
    print(f"📝 Access documentation at: http://localhost:8000{settings.API_V1_STR}/docs")
    
    if not all([settings.FIREBASE_PROJECT_ID, settings.FIREBASE_PRIVATE_KEY, settings.FIREBASE_CLIENT_EMAIL]):
        print("⚠️  WARNING: Firebase credentials are not fully configured in .env.")
        print("   Firestore features will remain unavailable until configured.")

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {"message": "Welcome to the Exam Backend"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
