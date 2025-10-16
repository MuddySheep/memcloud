"""
API v1 Router
Aggregates all v1 endpoints
"""
from fastapi import APIRouter

from app.api.v1.endpoints import instances, playground, deployment

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(
    instances.router,
    prefix="/instances",
    tags=["Instances"]
)

api_router.include_router(
    playground.router,
    prefix="/playground",
    tags=["Playground"]
)

api_router.include_router(
    deployment.router,
    prefix="/deployment",
    tags=["Deployment"]
)

# TODO: Add more routers as needed
# api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
# api_router.include_router(users.router, prefix="/users", tags=["Users"])
