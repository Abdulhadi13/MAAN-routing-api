from pydantic import BaseModel, Field
from typing import Optional, Any


EXAMPLE_PARAMETERS = {
    "origin": [39.830481912831424, 21.357049752855364],
    "destination": [39.87478018567941, 21.40458495008579],
    "waypoints": [
        [39.841362384648065, 21.388996441451567],
        [39.872728186529415, 21.40197484910052]
    ]
}


class RouteRequest(BaseModel):
    """Request body for the /v1/route endpoint."""

    origin: tuple[float, float] = Field(
        ...,
        description=(
            "Starting point of the route as **[longitude, latitude]** in WGS-84 "
            "decimal degrees. Snapped to the nearest road within **1000 m**."
        ),
        examples=[[39.830481912831424, 21.357049752855364]],
    )
    destination: tuple[float, float] = Field(
        ...,
        description=(
            "End point of the route as **[longitude, latitude]** in WGS-84 decimal "
            "degrees. Snapped to the nearest road within **1000 m**."
        ),
        examples=[[39.87478018567941, 21.40458495008579]],
    )
    waypoints: Optional[list[tuple[float, float]]] = Field(
        default=None,
        description=(
            "Ordered list of intermediate stops as **[[longitude, latitude], ...]** "
            "in WGS-84 decimal degrees. The route will pass through these points "
            "in the order provided, between the origin and destination."
            " Each waypoint is snapped to the nearest road within **1000 m**."
        ),
        examples=[[[39.841362384648065, 21.388996441451567], [39.872728186529415, 21.40197484910052]]],
    )

    model_config = {
        "json_schema_extra": {
            "example": EXAMPLE_PARAMETERS
        }
    }


class HealthResponse(BaseModel):
    status: str = Field(..., examples=["ok"])


# --- Response Models ---

class RouteSummary(BaseModel):
    distance: float = Field(..., description="Total route distance in **meters**.")
    duration: float = Field(..., description="Estimated travel time in **seconds**.")

class RouteProperties(BaseModel):
    summary: RouteSummary
    way_points: list[int] = Field(
        ...,
        description="Indices into the coordinates array marking origin, each waypoint, and destination.",
        examples=[[0, 114, 186, 188]],
    )

class RouteGeometry(BaseModel):
    type: str = Field("LineString", examples=["LineString"])
    coordinates: list[tuple[float, float]] = Field(
        ...,
        description="Ordered **[longitude, latitude]** pairs forming the route polyline.",
        examples=[[[39.830355, 21.357285], [39.831092, 21.357684], [39.874791, 21.404577]]],
    )

class RouteFeature(BaseModel):
    type: str = Field("Feature", examples=["Feature"])
    bbox: list[float] = Field(
        ...,
        description="Bounding box as **[min_lon, min_lat, max_lon, max_lat]**.",
        examples=[[39.802647, 21.35117, 39.874791, 21.404577]],
    )
    properties: RouteProperties
    geometry: RouteGeometry

class RouteEngineInfo(BaseModel):
    version: str = Field(..., examples=["8.0.0"])
    build_date: str = Field(..., examples=["2024-03-21T13:55:54Z"])
    graph_date: str = Field(..., examples=["2026-03-11T07:06:17Z"])

class RouteMetadata(BaseModel):
    attribution: str = Field(..., examples=["openrouteservice.org, OpenStreetMap contributors"])
    service: str = Field(..., examples=["routing"])
    timestamp: int = Field(..., description="Unix timestamp in milliseconds.", examples=[1773402417089])
    query: Any = Field(..., description="Echo of the original ORS request payload.")
    engine: RouteEngineInfo

class RouteResponse(BaseModel):
    type: str = Field("FeatureCollection", examples=["FeatureCollection"])
    bbox: list[float] = Field(
        ...,
        description="Bounding box of the full route as **[min_lon, min_lat, max_lon, max_lat]**.",
        examples=[[39.802647, 21.35117, 39.874791, 21.404577]],
    )
    features: list[RouteFeature]
    metadata: RouteMetadata

    model_config = {
        "json_schema_extra": {
            "example": {
                "type": "FeatureCollection",
                "bbox": [39.802647, 21.35117, 39.874791, 21.404577],
                "features": [
                    {
                        "type": "Feature",
                        "bbox": [39.802647, 21.35117, 39.874791, 21.404577],
                        "properties": {
                            "summary": {"distance": 17718.5, "duration": 1084.3},
                            "way_points": [0, 114, 186, 188]
                        },
                        "geometry": {
                            "type": "LineString",
                            "coordinates": [
                                [39.830355, 21.357285],
                                [39.831092, 21.357684],
                                ["..."]
                            ]
                        }
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
                        "graph_date": "2026-03-11T07:06:17Z"
                    }
                }
            }
        }
    }
