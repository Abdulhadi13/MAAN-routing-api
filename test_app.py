# test_app.py
import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_valid_route():
    response = client.post("/v1/route", json={
        "origin": [46.7167, 24.6867],  # 2 floats, as expected
        "destination": [46.7500, 24.7000]
    })
    # ORS won't be running in tests, so we expect 503 — not a 422
    assert response.status_code != 422

def test_origin_too_many_floats():
    response = client.post("/v1/route", json={
        "origin": [46.7167, 24.6867, 0.0, 0.0],  # 4 floats
        "destination": [46.7500, 24.7000]
    })
    assert response.status_code == 422  

def test_origin_wrong_type():
    response = client.post("/v1/route", json={
        "origin": ["not", "floats"],
        "destination": [46.7500, 24.7000]
    })
    assert response.status_code == 422

def test_missing_origin():
    response = client.post("/v1/route", json={
        "destination": [46.7500, 24.7000]
    })
    assert response.status_code == 422

def test_waypoints_wrong_shape():
    response = client.post("/v1/route", json={
        "origin": [46.7167, 24.6867],
        "destination": [46.7500, 24.7000],
        "waypoints": [[1.0, 2.0, 3.0]]  # inner list has 3 elements
    })
    assert response.status_code == 422  


# Integration test for ors service availability
def test_ors_is_reachable():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
