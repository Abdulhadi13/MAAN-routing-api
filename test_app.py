# test_app.py
from fastapi.testclient import TestClient

import app as app_module
from app import app

client = TestClient(app)

ROUTE_RESPONSE = {
    "type": "FeatureCollection",
    "bbox": [39.0, 21.0, 40.0, 22.0],
    "features": [
        {
            "type": "Feature",
            "bbox": [39.0, 21.0, 40.0, 22.0],
            "properties": {
                "summary": {"distance": 1000.0, "duration": 120.0},
                "way_points": [0, 1],
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [[39.0, 21.0], [40.0, 22.0]],
            },
        }
    ],
    "metadata": {
        "attribution": "openrouteservice.org, OpenStreetMap contributors",
        "service": "routing",
        "timestamp": 1773402417089,
        "query": {"profile": "driving-car", "format": "geojson"},
        "engine": {
            "version": "8.0.0",
            "build_date": "2024-03-21T13:55:54Z",
            "graph_date": "2026-03-11T07:06:17Z",
        },
    },
}


class FakeORSResponse:
    status_code = 200
    text = "{}"

    def raise_for_status(self):
        return None

    def json(self):
        return ROUTE_RESPONSE


class FakeAsyncClient:
    requests = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return None

    async def post(self, url, json, headers, timeout):
        self.requests.append(
            {
                "url": url,
                "json": json,
                "headers": headers,
                "timeout": timeout,
            }
        )
        return FakeORSResponse()


def test_valid_route(monkeypatch):
    async def fake_get_avoid_polygons_geometry(origin, destination):
        return None

    monkeypatch.setattr(
        app_module,
        "get_avoid_polygons_geometry",
        fake_get_avoid_polygons_geometry,
    )
    monkeypatch.setattr(app_module.httpx, "AsyncClient", FakeAsyncClient)

    response = client.post(
        "/v1/route",
        json={
            "origin": [46.7167, 24.6867],
            "destination": [46.7500, 24.7000],
        },
    )

    assert response.status_code != 422


def test_route_sends_avoid_polygons_from_database(monkeypatch):
    avoid_geometry = {
        "type": "MultiPolygon",
        "coordinates": [[[[39.0, 21.0], [40.0, 21.0], [40.0, 22.0], [39.0, 21.0]]]],
    }

    async def fake_get_avoid_polygons_geometry(origin, destination):
        assert origin == (46.7167, 24.6867)
        assert destination == (46.75, 24.7)
        return avoid_geometry

    FakeAsyncClient.requests.clear()
    monkeypatch.setattr(
        app_module,
        "get_avoid_polygons_geometry",
        fake_get_avoid_polygons_geometry,
    )
    monkeypatch.setattr(app_module.httpx, "AsyncClient", FakeAsyncClient)

    response = client.post(
        "/v1/route",
        json={
            "origin": [46.7167, 24.6867],
            "destination": [46.7500, 24.7000],
        },
    )

    assert response.status_code == 200
    assert FakeAsyncClient.requests[-1]["json"]["options"] == {
        "avoid_polygons": avoid_geometry
    }


def test_route_omits_avoid_polygons_when_database_returns_no_geometry(monkeypatch):
    async def fake_get_avoid_polygons_geometry(origin, destination):
        return None

    FakeAsyncClient.requests.clear()
    monkeypatch.setattr(
        app_module,
        "get_avoid_polygons_geometry",
        fake_get_avoid_polygons_geometry,
    )
    monkeypatch.setattr(app_module.httpx, "AsyncClient", FakeAsyncClient)

    response = client.post(
        "/v1/route",
        json={
            "origin": [46.7167, 24.6867],
            "destination": [46.7500, 24.7000],
        },
    )

    assert response.status_code == 200
    assert "options" not in FakeAsyncClient.requests[-1]["json"]


def test_route_returns_503_when_database_lookup_fails(monkeypatch):
    async def fake_get_avoid_polygons_geometry(origin, destination):
        raise app_module.RoutingRulesDatabaseError("database unavailable")

    monkeypatch.setattr(
        app_module,
        "get_avoid_polygons_geometry",
        fake_get_avoid_polygons_geometry,
    )

    response = client.post(
        "/v1/route",
        json={
            "origin": [46.7167, 24.6867],
            "destination": [46.7500, 24.7000],
        },
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "Routing rules database unavailable"}


def test_origin_too_many_floats():
    response = client.post(
        "/v1/route",
        json={
            "origin": [46.7167, 24.6867, 0.0, 0.0],
            "destination": [46.7500, 24.7000],
        },
    )
    assert response.status_code == 422


def test_origin_wrong_type():
    response = client.post(
        "/v1/route",
        json={
            "origin": ["not", "floats"],
            "destination": [46.7500, 24.7000],
        },
    )
    assert response.status_code == 422


def test_missing_origin():
    response = client.post(
        "/v1/route",
        json={
            "destination": [46.7500, 24.7000],
        },
    )
    assert response.status_code == 422


def test_waypoints_wrong_shape():
    response = client.post(
        "/v1/route",
        json={
            "origin": [46.7167, 24.6867],
            "destination": [46.7500, 24.7000],
            "waypoints": [[1.0, 2.0, 3.0]],
        },
    )
    assert response.status_code == 422


def test_ors_is_reachable():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
