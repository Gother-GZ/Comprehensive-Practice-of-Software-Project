from fastapi import APIRouter

from app.api.v1 import auth, integration, system, users, vsp

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(vsp.router, prefix="/vsp", tags=["vsp"])
api_router.include_router(system.router, prefix="/system", tags=["system"])
api_router.include_router(integration.router, tags=["integration"])

