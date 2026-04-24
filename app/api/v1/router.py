"""v1 API router — aggregates all v1 endpoints."""

from fastapi import APIRouter

from app.api.v1 import attendance, bills, interpellations, legislators, votes

api_router = APIRouter(prefix="/v1")
api_router.include_router(legislators.router)
api_router.include_router(attendance.router)
api_router.include_router(votes.router)
api_router.include_router(bills.router)
api_router.include_router(interpellations.router)
