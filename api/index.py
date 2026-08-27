"""Vercel Python entrypoint for the AION FastAPI runtime."""

from fastapi import FastAPI

from aion.main import app as runtime_app

app = FastAPI()
app.mount("/api", runtime_app)
app.mount("/", runtime_app)
