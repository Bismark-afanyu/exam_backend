from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME, openapi_url=f"{settings.API_V1_STR}/openapi.json"
)


@app.on_event("startup")
async def startup_event():
    print("🚀 Application started successfully!")
    print(
        f"📝 Access documentation at: http://localhost:8000{settings.API_V1_STR}/docs"
    )

    firestore_configured = (
        settings.FIREBASE_SERVICE_ACCOUNT_PATH
        or (
            settings.FIREBASE_PROJECT_ID
            and settings.FIREBASE_PRIVATE_KEY
            and settings.FIREBASE_CLIENT_EMAIL
        )
    )
    if not firestore_configured:
        print("⚠️  WARNING: Firebase credentials are not fully configured in .env.")
        print("   Firestore features will remain unavailable until configured.")


# Set all CORS enabled origins
origins = [
    "http://localhost:3000",
    "http://localhost:3001",
]
if settings.BACKEND_CORS_ORIGINS:
    origins = [o.strip() for o in settings.BACKEND_CORS_ORIGINS.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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
