WITH request_points AS (
    SELECT
        ST_SetSRID(ST_MakePoint(%(origin_lon)s, %(origin_lat)s), 4326) AS origin_point,
        ST_SetSRID(ST_MakePoint(%(destination_lon)s, %(destination_lat)s), 4326) AS destination_point
),
matched_rules AS (
    SELECT rr.*
    FROM maan_routing.routing_rules rr
    CROSS JOIN request_points rp
    WHERE rr.active = TRUE
      AND (
          rr.origin IS NULL
          OR ST_Covers(rr.origin, rp.origin_point)
      )
      AND (
          rr.destination IS NULL
          OR ST_Covers(rr.destination, rp.destination_point)
      )
),
avoid_geometry AS (
    SELECT ST_Multi(ST_UnaryUnion(ST_Collect(avoid))) AS geom
    FROM matched_rules
)
SELECT json_build_object(
    'type', 'Feature',
    'geometry', CASE
        WHEN geom IS NULL THEN NULL
        ELSE ST_AsGeoJSON(geom)::json
    END,
    'properties', json_build_object()
) AS avoid_geojson
FROM avoid_geometry;
