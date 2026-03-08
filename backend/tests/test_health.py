import pytest
from httpx import ASGITransport, AsyncClient

from main import app


def make_client():
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    )


@pytest.mark.anyio
async def test_health_endpoint():
    async with make_client() as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("ok", "degraded")
    assert data["service"] == "loglens-api"
    assert "database" in data


@pytest.mark.anyio
async def test_root_endpoint():
    async with make_client() as client:
        resp = await client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert "LogLens API" in data["service"]
