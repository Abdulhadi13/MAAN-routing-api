CREATE EXTENSION IF NOT EXISTS postgis;

CREATE SCHEMA IF NOT EXISTS maan_routing;

CREATE TABLE IF NOT EXISTS maan_routing.routing_rules (
    id BIGSERIAL PRIMARY KEY,
    rule_description TEXT NOT NULL,
    origin geometry(MultiPolygon, 4326),
    destination geometry(MultiPolygon, 4326),
    avoid geometry(MultiPolygon, 4326) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT routing_rules_origin_valid
        CHECK (origin IS NULL OR ST_IsValid(origin)),
    CONSTRAINT routing_rules_destination_valid
        CHECK (destination IS NULL OR ST_IsValid(destination)),
    CONSTRAINT routing_rules_avoid_valid
        CHECK (ST_IsValid(avoid)),

    CONSTRAINT routing_rules_origin_not_empty
        CHECK (origin IS NULL OR NOT ST_IsEmpty(origin)),
    CONSTRAINT routing_rules_destination_not_empty
        CHECK (destination IS NULL OR NOT ST_IsEmpty(destination)),
    CONSTRAINT routing_rules_avoid_not_empty
        CHECK (NOT ST_IsEmpty(avoid))
);

CREATE INDEX IF NOT EXISTS routing_rules_origin_gix
    ON maan_routing.routing_rules
    USING GIST (origin)
    WHERE active = TRUE AND origin IS NOT NULL;

CREATE INDEX IF NOT EXISTS routing_rules_destination_gix
    ON maan_routing.routing_rules
    USING GIST (destination)
    WHERE active = TRUE AND destination IS NOT NULL;

CREATE INDEX IF NOT EXISTS routing_rules_active_idx
    ON maan_routing.routing_rules (active);
