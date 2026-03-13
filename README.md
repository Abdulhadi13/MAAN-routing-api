# معن — MAAN Routing API

A driving routing API for Makkah built with **FastAPI**, backed by a self-hosted **OpenRouteService (ORS)** instance. Routes automatically avoid restricted geofenced areas defined in `data/geofences_to_avoid.geojson`.

---

## Requirements

- [Docker](https://docs.docker.com/get-docker/) (with the Compose plugin)
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (Python package manager)

---

## Project Structure

```
.
├── app.py                          # FastAPI application
├── config.py                       # ORS base URL configuration
├── models.py                       # Pydantic request/response models
├── test_app.py                     # Tests
├── pyproject.toml
├── docker-compose.yml              # ORS container definition
├── data/
│   └── geofences_to_avoid.geojson  # Restricted areas excluded from routes
└── ors-docker/
    ├── config/
    │   └── ors-maan-config.yml     # ORS configuration
    ├── files/                      # Place your OSM source file here
    ├── graphs/                     # Built automatically by ORS on first run
    ├── elevation_cache/
    └── logs/
```

---

## Setup

### 1. Add the OSM source file

`ors-docker/files/makkah.osm.gz` is already included. If you want to use a different OSM file, replace it and update `ors.engine.source_file` in `ors-docker/config/ors-maan-config.yml` accordingly.

### 2. Set directory permissions

ORS runs as user `1000:1000` inside the container. Run this once before the first start:

```bash
mkdir -p ors-docker/config ors-docker/elevation_cache ors-docker/files ors-docker/graphs ors-docker/logs
sudo chown -R 1000:1000 ors-docker/
```

### 3. Start the ORS container

```bash
docker compose up
```

ORS will build the routing graphs from the OSM file on the **first run** — this takes less than a minute for the Makkah network. Subsequent starts reuse the cached graphs and are much faster.

The ORS API will be available at `http://localhost:8082/ors/v2`.

### 4. Install FastAPI dependencies

```bash
uv sync
```

### 5. Run the API

```bash
fastapi dev app.py --host 0.0.0.0 --port 8000
```

- `--host 0.0.0.0` makes the API accessible from other machines on the network.
- `--port` can be changed to any available port.

Interactive docs: `http://localhost:8000/docs`

---

## Configuration

`config.py` holds the ORS service URL used by the FastAPI app:

```python
ORS_BASE_URL = "http://localhost:8082/ors/v2"
```

Update this value if ORS is running on a different host or port.

---

## API Endpoints

### `GET /health`

Returns a simple status check.

**Response**
```json
{ "status": "ok" }
```

---

### `POST /v1/route`

Computes a driving route from an origin to a destination, with optional intermediate waypoints. All routes avoid the geofenced areas loaded from `data/geofences_to_avoid.geojson`.

**Request body**

| Field         | Type                        | Required | Description                                              |
|---------------|-----------------------------|----------|----------------------------------------------------------|
| `origin`      | `[longitude, latitude]`     | Yes      | Starting point in WGS-84 decimal degrees                 |
| `destination` | `[longitude, latitude]`     | Yes      | End point in WGS-84 decimal degrees                      |
| `waypoints`   | `[[lon, lat], ...]`         | No       | Ordered intermediate stops                               |

> Each coordinate is snapped to the nearest road within **1000 m**.

**Example request**

```json
{
  "origin": [39.830481912831424, 21.357049752855364],
  "destination": [39.87478018567941, 21.40458495008579],
  "waypoints": [
    [39.841362384648065, 21.388996441451567],
    [39.872728186529415, 21.40197484910052]
  ]
}
```

**Response**

A GeoJSON `FeatureCollection` containing the route geometry, total distance (meters), and estimated duration (seconds).

