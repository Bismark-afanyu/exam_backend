import firebase_admin
from firebase_admin import credentials, firestore, storage

from app.core.config import settings


def get_db():
    try:
        # Check if app is already initialized
        firebase_admin.get_app()
    except ValueError:
        if settings.FIREBASE_SERVICE_ACCOUNT_PATH:
            cred = credentials.Certificate(settings.FIREBASE_SERVICE_ACCOUNT_PATH)
        else:
            # Construct service account info from env vars
            service_account_info = {
                "project_id": settings.FIREBASE_PROJECT_ID,
                "private_key": settings.FIREBASE_PRIVATE_KEY.replace("\\n", "\n"),
                "client_email": settings.FIREBASE_CLIENT_EMAIL,
                "type": "service_account",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
            cred = credentials.Certificate(service_account_info)

        firebase_admin.initialize_app(cred, {
            "storageBucket": settings.FIREBASE_STORAGE_BUCKET
        })

    return firestore.client()


def get_storage_bucket():
    """Returns the Firebase Storage bucket."""
    return storage.bucket()
