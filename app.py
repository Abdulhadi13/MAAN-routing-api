from fastapi import FastAPI, HTTPException
import httpx
import json
from pathlib import Path
from loguru import logger
from models import (
    RouteRequest,
    HealthResponse,
    RouteResponse,
)
from config import ORS_BASE_URL
from logging_config import setup_logging

setup_logging()


app = FastAPI(
    title="MAAN Routing API",
    description=(
        "A routing API that computes driving directions between an origin and a "
        "destination, with optional intermediate waypoints. Routes automatically "
        "avoid restricted geofenced areas configured on the server."
    ),
    version="1.0.0",
)

# Load geofences once at startup
_geofences_path = Path(__file__).parent / "data" / "geofences_to_avoid.geojson"
logger.info("Loading geofences from {}", _geofences_path)
with open(_geofences_path) as f:
    _geofence_data = json.load(f)
AVOID_POLYGONS = _geofence_data["geometry"]  # MultiPolygon geometry
logger.info(
    "Loaded {} geofence polygon(s)",
    len(AVOID_POLYGONS.get("coordinates", [])),
)


@app.get(
    "/health",
    summary="Health check",
    description="Returns a simple status indicating the API is running.",
    tags=["Operations"],
    response_model=HealthResponse,
)
def health():
    logger.debug("Health check requested")
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
    logger.info(
        "Route request | origin={} destination={} waypoints={}",
        request.origin,
        request.destination,
        request.waypoints,
    )
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
            logger.success(
                "Route computed successfully | status={}", response.status_code
            )
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                "ORS returned error | status={} body={}",
                e.response.status_code,
                e.response.text,
            )
            raise HTTPException(
                status_code=e.response.status_code,
                detail=e.response.text
            )
        except httpx.RequestError as e:
            logger.error("ORS service unreachable | error={}", e)
            raise HTTPException(
                status_code=503,
                detail=f"ORS service unavailable: {str(e)}"
            )
