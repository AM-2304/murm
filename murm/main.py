"""ASGI entry point. Run with: uvicorn murm.main:app"""
from murm.api.app import create_app

app = create_app()
