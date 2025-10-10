"""
API v1 Router
Aggregates all v1 endpoints
"""
from fastapi import APIRouter

from app.api.v1.endpoints import instances

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(
    instances.router,
    prefix="/instances",
    tags=["Instances"]
)

# TODO: Add more routers as needed
# api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
# api_router.include_router(users.router, prefix="/users", tags=["Users"])
