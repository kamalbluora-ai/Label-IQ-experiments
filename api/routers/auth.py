from fastapi import APIRouter
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from storage import storage

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
async def login():
    """Mock login - returns a demo user."""
    user = storage.get_mock_user()
    return user


@router.post("/logout")
async def logout():
    """Mock logout."""
    return {"message": "Logged out successfully"}
