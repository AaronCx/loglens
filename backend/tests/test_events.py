import pytest
from httpx import ASGITransport, AsyncClient

from main import app

API_HEADERS = {"X-API-Key": "test-key"}

VALID_EVENT = {
    "severity": "error",
    "service": "test-service",
    "message": "Something went wrong",
    "environment": "testing",
}


def make_client():
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    )


@pytest.mark.anyio
async def test_create_event():
    async with make_client() as client:
        resp = await client.post("/events", json=VALID_EVENT, headers=API_HEADERS)
    assert resp.status_code == 201
    data = resp.json()
    assert data["severity"] == "error"
    assert data["service"] == "test-service"
    assert data["message"] == "Something went wrong"
    assert data["environment"] == "testing"
    assert "id" in data
    assert "timestamp" in data


@pytest.mark.anyio
async def test_create_event_missing_api_key():
    async with make_client() as client:
        resp = await client.post("/events", json=VALID_EVENT)
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_create_event_invalid_api_key():
    async with make_client() as client:
        resp = await client.post(
            "/events", json=VALID_EVENT, headers={"X-API-Key": "wrong-key"}
        )
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_create_event_invalid_severity():
    async with make_client() as client:
        event = {**VALID_EVENT, "severity": "catastrophic"}
        resp = await client.post("/events", json=event, headers=API_HEADERS)
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_create_event_empty_message():
    async with make_client() as client:
        event = {**VALID_EVENT, "message": ""}
        resp = await client.post("/events", json=event, headers=API_HEADERS)
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_create_event_with_stack_trace():
    async with make_client() as client:
        event = {
            **VALID_EVENT,
            "stack_trace": "Traceback (most recent call last):\n  File ...",
            "metadata": {"request_id": "abc-123", "user_id": 42},
        }
        resp = await client.post("/events", json=event, headers=API_HEADERS)
    assert resp.status_code == 201
    data = resp.json()
    assert data["stack_trace"] is not None
    assert data["metadata"]["request_id"] == "abc-123"


@pytest.mark.anyio
async def test_create_event_metadata_too_large():
    async with make_client() as client:
        event = {**VALID_EVENT, "metadata": {"big": "x" * 100_000}}
        resp = await client.post("/events", json=event, headers=API_HEADERS)
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_list_events():
    async with make_client() as client:
        await client.post("/events", json=VALID_EVENT, headers=API_HEADERS)
        await client.post(
            "/events",
            json={**VALID_EVENT, "severity": "critical", "service": "other-svc"},
            headers=API_HEADERS,
        )
        resp = await client.get("/events")
    assert resp.status_code == 200
    data = resp.json()
    assert "events" in data
    assert "total" in data
    assert data["total"] >= 2
    assert data["page"] == 1
    assert data["page_size"] == 50


@pytest.mark.anyio
async def test_list_events_filter_severity():
    async with make_client() as client:
        await client.post(
            "/events",
            json={**VALID_EVENT, "severity": "info"},
            headers=API_HEADERS,
        )
        resp = await client.get("/events?severity=info")
    assert resp.status_code == 200
    data = resp.json()
    for event in data["events"]:
        assert event["severity"] == "info"


@pytest.mark.anyio
async def test_list_events_search():
    async with make_client() as client:
        await client.post(
            "/events",
            json={**VALID_EVENT, "message": "UniqueSearchTerm42"},
            headers=API_HEADERS,
        )
        resp = await client.get("/events?search=UniqueSearchTerm42")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert all("UniqueSearchTerm42" in e["message"] for e in data["events"])


@pytest.mark.anyio
async def test_list_events_pagination():
    async with make_client() as client:
        resp = await client.get("/events?page=1&page_size=2")
    assert resp.status_code == 200
    data = resp.json()
    assert data["page_size"] == 2
    assert len(data["events"]) <= 2


@pytest.mark.anyio
async def test_get_event_by_id():
    async with make_client() as client:
        create_resp = await client.post("/events", json=VALID_EVENT, headers=API_HEADERS)
        event_id = create_resp.json()["id"]
        resp = await client.get(f"/events/{event_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == event_id


@pytest.mark.anyio
async def test_get_event_not_found():
    async with make_client() as client:
        resp = await client.get("/events/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_get_stats():
    async with make_client() as client:
        await client.post("/events", json=VALID_EVENT, headers=API_HEADERS)
        resp = await client.get("/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "by_severity" in data
    assert "by_service" in data
    assert data["total"] >= 1


@pytest.mark.anyio
async def test_get_timeseries():
    async with make_client() as client:
        await client.post("/events", json=VALID_EVENT, headers=API_HEADERS)
        resp = await client.get("/stats/timeseries?hours=24")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.anyio
async def test_get_timeseries_invalid_hours():
    async with make_client() as client:
        resp = await client.get("/stats/timeseries?hours=0")
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_clear_events():
    async with make_client() as client:
        await client.post("/events", json=VALID_EVENT, headers=API_HEADERS)
        resp = await client.delete("/events", headers=API_HEADERS)
    assert resp.status_code == 204


@pytest.mark.anyio
async def test_clear_events_requires_api_key():
    async with make_client() as client:
        resp = await client.delete("/events")
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_create_all_severities():
    async with make_client() as client:
        for sev in ["info", "warning", "error", "critical"]:
            resp = await client.post(
                "/events",
                json={**VALID_EVENT, "severity": sev},
                headers=API_HEADERS,
            )
            assert resp.status_code == 201
            assert resp.json()["severity"] == sev
