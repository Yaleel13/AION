"""Vercel Python entrypoint for the AION FastAPI runtime."""

from aion.main import app

# Vercel detects this ASGI app from api/index.py.
