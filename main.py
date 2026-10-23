"""FastAPI entry point: uvicorn main:app --reload"""
from backend.api import app
__all__ = ["app"]
