import json
from pathlib import Path
from typing import Any, cast
from psycopg.abc import QueryNoTemplate

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from config import DATABASE_CONNINFO


QUERY_PATH = (
    Path(__file__).parent
    / "database"
    / "script"
    / "queries"
    / "match-routing-rules-geojson.sql"
)
MATCH_ROUTING_RULES_GEOJSON_SQL: QueryNoTemplate = cast(QueryNoTemplate, QUERY_PATH.read_text())

_pool: AsyncConnectionPool | None = None


class RoutingRulesDatabaseError(RuntimeError):
    """Raised when routing-rule lookup cannot be completed."""


async def open_database_pool() -> None:
    global _pool
    if _pool is not None:
        return

    _pool = AsyncConnectionPool(
        conninfo=DATABASE_CONNINFO,
        open=False,
        kwargs={"row_factory": dict_row},
    )
    await _pool.open()


async def close_database_pool() -> None:
    global _pool
    if _pool is None:
        return

    await _pool.close()
    _pool = None


async def get_avoid_polygons_geometry(
    origin: tuple[float, float],
    destination: tuple[float, float],
) -> dict[str, Any] | None:
    if _pool is None:
        raise RoutingRulesDatabaseError("Database pool is not initialized")

    params = {
        "origin_lon": origin[0],
        "origin_lat": origin[1],
        "destination_lon": destination[0],
        "destination_lat": destination[1],
    }

    try:
        async with _pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(MATCH_ROUTING_RULES_GEOJSON_SQL, params)
                row = cast(dict[str, Any] | None, await cursor.fetchone())
    except psycopg.Error as exc:
        raise RoutingRulesDatabaseError("Routing-rule lookup failed") from exc

    if not row or not row["avoid_geojson"]:
        return None

    avoid_geojson = row["avoid_geojson"]
    if isinstance(avoid_geojson, str):
        avoid_geojson = json.loads(avoid_geojson)

    return cast(dict[str, Any], avoid_geojson).get("geometry")
