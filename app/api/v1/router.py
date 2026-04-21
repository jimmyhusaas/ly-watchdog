"""v1 API router — aggregates all v1 endpoints."""

from fastapi import APIRouter

from app.api.v1 import legislators

api_router = APIRouter(prefix="/v1")
api_router.include_router(legislators.router)
