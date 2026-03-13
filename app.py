from fastapi import FastAPI, HTTPException
import httpx
import json
from pathlib import Path
from models import (
    RouteRequest,
    HealthResponse,
    RouteResponse,
)

app = FastAPI(
    title="MAAN Routing API",
    description=(
        "A routing API that computes driving directions between an origin and a "
        "destination, with optional intermediate waypoints. Routes automatically "
        "avoid restricted geofenced areas configured on the server."
    ),
    version="1.0.0",
)

ORS_BASE_URL = "http://localhost:8082/ors/v2"

# Load geofences once at startup
_geofences_path = Path(__file__).parent / "data" / "geofences_to_avoid.geojson"
with open(_geofences_path) as f:
    _geofence_data = json.load(f)
AVOID_POLYGONS = _geofence_data["geometry"]  # MultiPolygon geometry


@app.get(
    "/health",
    summary="Health check",
    description="Returns a simple status indicating the API is running.",
    tags=["Operations"],
    response_model=HealthResponse,
)
def health():
    return HealthResponse(status="ok")


@app.post(
    "/v1/route",
    summary="Calculate driving route",
    description=(
        "Computes a driving route from **origin** to **destination**, optionally "
        "passing through ordered **waypoints**. Returns a GeoJSON FeatureCollection "
        "with the route geometry.\n\n"
        "**Note:** Each coordinate is snapped to the nearest road segment within "
        "**1000 m**. If no road is found within that radius, the request will fail."
    ),
    response_description="GeoJSON FeatureCollection containing the computed route.",
    tags=["Routing"],
    response_model=RouteResponse,
    response_model_exclude_none=True,
)
async def get_route(request: RouteRequest):
    coordinates = [request.origin] + (request.waypoints or []) + [request.destination]

    payload = {
        "coordinates": coordinates,
        "options": {
            "avoid_polygons": AVOID_POLYGONS
        },
        "instructions": False,
        "radiuses": [1000] # Snap points within 1000m of the provided coordinates, to allow for some flexibility in matching
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{ORS_BASE_URL}/directions/driving-car/geojson",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=e.response.text
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"ORS service unavailable: {str(e)}"
            )
