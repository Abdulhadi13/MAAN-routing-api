WITH request_points AS (
    SELECT
        ST_SetSRID(ST_MakePoint(:origin_lon, :origin_lat), 4326) AS origin_point,
        ST_SetSRID(ST_MakePoint(:destination_lon, :destination_lat), 4326) AS destination_point
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
)
SELECT ST_Multi(ST_UnaryUnion(ST_Collect(avoid))) AS avoid_multipolygon
FROM matched_rules;
