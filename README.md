# معن — MAAN Routing API

A driving routing API for Makkah built with **FastAPI**, backed by a self-hosted **OpenRouteService (ORS)** instance. Routes automatically avoid restricted geofenced areas matched from PostGIS routing rules.

---

## Requirements

- [Docker](https://docs.docker.com/get-docker/) (with the Compose plugin)
- At least 2 GB of memory available to ORS, as configured in `docker-compose.yml`

Installing [uv](https://docs.astral.sh/uv/getting-started/installation/) on the
host is optional. The API images include a pinned version of uv.

---

## Project Structure

```
.
├── app.py                          # FastAPI application
├── config.py                       # ORS, database, and log dir configuration
├── database.py                     # Raw SQL database access
├── logging_config.py               # Loguru logging setup
├── models.py                       # Pydantic request/response models
├── test_app.py                     # Tests
├── pyproject.toml
├── uv.lock
├── Dockerfile                      # Production and development API image
├── docker-compose.yml              # Production API, ORS, and PostGIS stack
├── docker-compose.dev.yml          # Development API override with reload
├── data/
│   └── geofences_to_avoid.geojson  # Legacy/static geofence data
├── database/                       # PostGIS init scripts and raw SQL queries
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

Place the configured OSM/PBF source in `ors-docker/files/`. If you use a
different file, update `ors.engine.source_file` in `docker-compose.yml` or the
corresponding ORS configuration.

### 2. Set directory permissions

ORS runs as user `1000:1000` inside the container. Run this once before the first start:

```bash
mkdir -p ors-docker/config ors-docker/elevation_cache ors-docker/files ors-docker/graphs ors-docker/logs
sudo chown -R 1000:1000 ors-docker/
```

### 3. Configure environment values

```bash
cp .env.example .env
```

The defaults are suitable for local development. Change `POSTGRES_PASSWORD`
before deploying the stack to a shared or production host. `.env` is ignored by
Git and is not copied into the API image.

### 4. Start the production stack

```bash
docker compose up --build -d
```

Compose waits for PostGIS and ORS to report healthy before starting the API.
ORS builds its routing graphs on the first run, which can take several minutes;
subsequent starts reuse the cached graphs.

Service URLs:

- API: `http://localhost:8000`
- Interactive API documentation: `http://localhost:8000/docs`
- ORS: `http://localhost:8082/ors/v2`
- PostGIS: `localhost:15432`

Check status and follow logs with:

```bash
docker compose ps
docker compose logs -f api
```

Stop the stack without deleting the PostGIS volume:

```bash
docker compose down
```

## Development

The development override installs the `dev` dependency group and bind-mounts
only the API source files and runtime SQL query. FastAPI reloads when those files
change.

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Run the test suite in the development image:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm api pytest
```

When dependencies change, rebuild the API image:

```bash
docker compose build --no-cache api
```

For development without Docker, install uv and run:

```bash
uv sync
uv run fastapi dev app.py --host 0.0.0.0 --port 8000
```

The non-containerized API expects PostGIS on `localhost:15432` and ORS on
`localhost:8082` unless their environment variables are overridden.

---

## Configuration

Copy `.env.example` to `.env` to configure Compose. The API reads its service
addresses and database settings from environment variables:

| Variable            | Host default                   | Compose value                  |
| ------------------- | ------------------------------ | ------------------------------ |
| `API_PORT`          | `8000`                         | Host port mapped to API `8000` |
| `ORS_BASE_URL`      | `http://localhost:8082/ors/v2` | `http://ors-app:8082/ors/v2`   |
| `POSTGRES_HOST`     | `localhost`                    | `postgis`                      |
| `POSTGRES_PORT`     | `15432`                        | `5432`                         |
| `POSTGRES_DB`       | `maan_routing`                 | `${POSTGRES_DB}`               |
| `POSTGRES_USER`     | `postgres`                     | `${POSTGRES_USER}`             |
| `POSTGRES_PASSWORD` | `postgres`                     | `${POSTGRES_PASSWORD}`         |

The Compose variables use the development-friendly values from `.env.example`
when no `.env` file is present.

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

Computes a driving route from an origin to a destination, with optional intermediate waypoints. Routes avoid areas matched from active rows in `maan_routing.routing_rules` for the requested origin and destination.

**Request body**

| Field         | Type                    | Required | Description                              |
| ------------- | ----------------------- | -------- | ---------------------------------------- |
| `origin`      | `[longitude, latitude]` | Yes      | Starting point in WGS-84 decimal degrees |
| `destination` | `[longitude, latitude]` | Yes      | End point in WGS-84 decimal degrees      |
| `waypoints`   | `[[lon, lat], ...]`     | No       | Ordered intermediate stops               |

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
