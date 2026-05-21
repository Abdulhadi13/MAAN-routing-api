-- Enable PostGIS support for geometry types, spatial validation functions, and
-- spatial indexes used by the routing rules table.
CREATE EXTENSION IF NOT EXISTS postgis;

-- Keep MAAN routing database objects grouped under a dedicated schema.
CREATE SCHEMA IF NOT EXISTS maan_routing;

-- Stores routing rules with optional origin/destination areas and a required
-- avoid area. Timestamps are managed by defaults and the update trigger below.
CREATE TABLE IF NOT EXISTS maan_routing.routing_rules (
    id BIGSERIAL PRIMARY KEY,
    rule_description TEXT NOT NULL,
    origin geometry(MultiPolygon, 4326),
    destination geometry(MultiPolygon, 4326),
    avoid geometry(MultiPolygon, 4326) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Accept NULL origin/destination geometries, but require every provided
    -- geometry to be spatially valid.
    CONSTRAINT routing_rules_origin_valid
        CHECK (origin IS NULL OR ST_IsValid(origin)),
    CONSTRAINT routing_rules_destination_valid
        CHECK (destination IS NULL OR ST_IsValid(destination)),
    CONSTRAINT routing_rules_avoid_valid
        CHECK (ST_IsValid(avoid)),

    -- Empty geometries are not useful routing boundaries.
    CONSTRAINT routing_rules_origin_not_empty
        CHECK (origin IS NULL OR NOT ST_IsEmpty(origin)),
    CONSTRAINT routing_rules_destination_not_empty
        CHECK (destination IS NULL OR NOT ST_IsEmpty(destination)),
    CONSTRAINT routing_rules_avoid_not_empty
        CHECK (NOT ST_IsEmpty(avoid))
);

-- Reusable trigger function for tables with an updated_at column.
CREATE OR REPLACE FUNCTION maan_routing.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Keep updated_at current whenever a routing rule is changed.
DROP TRIGGER IF EXISTS routing_rules_set_updated_at
    ON maan_routing.routing_rules;

CREATE TRIGGER routing_rules_set_updated_at
BEFORE UPDATE ON maan_routing.routing_rules
FOR EACH ROW
EXECUTE FUNCTION maan_routing.set_updated_at();

-- Spatial indexes accelerate geofence lookups for active rules. Partial indexes
-- avoid storing inactive rows or optional NULL geometries.
CREATE INDEX IF NOT EXISTS routing_rules_origin_gix
    ON maan_routing.routing_rules
    USING GIST (origin)
    WHERE active = TRUE AND origin IS NOT NULL;

CREATE INDEX IF NOT EXISTS routing_rules_destination_gix
    ON maan_routing.routing_rules
    USING GIST (destination)
    WHERE active = TRUE AND destination IS NOT NULL;

-- Supports quickly filtering enabled/disabled rules.
CREATE INDEX IF NOT EXISTS routing_rules_active_idx
    ON maan_routing.routing_rules (active);
