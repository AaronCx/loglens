import os

from fastapi import Header, HTTPException

API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise RuntimeError(
        "API_KEY environment variable is required (no default). "
        "Generate one with `openssl rand -hex 32`."
    )


def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    """Simple API key check for non-project-scoped endpoints."""
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key
