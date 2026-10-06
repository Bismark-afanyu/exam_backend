from fastapi import APIRouter

from app.api.v1.endpoints import auth, community, exams, team

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(community.router, prefix="/community", tags=["community"])
api_router.include_router(exams.router, prefix="/exams", tags=["exams"])
api_router.include_router(team.router, prefix="/team", tags=["team"])
