INSERT INTO "Nodes" ("Id", "NodeId", "CreatedAt", "UpdatedAt", "LongName", "ShortName", "RegionCode", "Latitude", "Longitude", "LastSeen", "Ignored")
VALUES
    (111111, 111111, NOW(), NOW(), 'Test Node Paris',      'PAR', 'Eu868', 48.8566,  2.3522, NOW(), false),
    (222222, 222222, NOW(), NOW(), 'Test Node Lyon',       'LYO', 'Eu868', 45.7640,  4.8357, NOW(), false),
    (333333, 333333, NOW(), NOW(), 'Test Node Marseille',  'MAR', 'Eu868', 43.2965,  5.3698, NOW(), false),
    (444444, 444444, NOW(), NOW(), 'Test Node Toulouse',   'TLS', 'Eu868', 43.6047,  1.4442, NOW(), false),
    (555555, 555555, NOW(), NOW(), 'Test Node Versailles', 'VER', 'Eu868', 48.8014,  2.1301, NOW(), false)
    ON CONFLICT DO NOTHING;

CREATE TABLE "CoverageMaps" (
                                "NodeId" BIGINT PRIMARY KEY,
                                "GeoJSON" JSONB NOT NULL,
                                "CalculatedAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                                "Parameters" JSONB,
                                CONSTRAINT "FK_CoverageMaps_Nodes_NodeId"
                                    FOREIGN KEY ("NodeId")
                                        REFERENCES "Nodes"("Id")
                                        ON DELETE CASCADE
);

CREATE INDEX "IX_CoverageMaps_CalculatedAt" ON "CoverageMaps"("CalculatedAt");

INSERT INTO "CoverageMaps" ("NodeId", "GeoJSON", "CalculatedAt", "Parameters")
VALUES
    (111111, '{"type":"Polygon","coordinates":[[[2.3522,49.3066],[2.8922,49.1566],[3.0922,48.8566],[2.8922,48.5566],[2.3522,48.4066],[1.8122,48.5566],[1.6122,48.8566],[1.8122,49.1566],[2.3522,49.3066]]]}', NOW(), '{"node":"Paris","radius_km":50}'),
    (222222, '{"type":"Polygon","coordinates":[[[4.8357,46.2140],[5.3757,46.0640],[5.5757,45.7640],[5.3757,45.4640],[4.8357,45.3140],[4.2957,45.4640],[4.0957,45.7640],[4.2957,46.0640],[4.8357,46.2140]]]}', NOW(), '{"node":"Lyon","radius_km":50}'),
    (333333, '{"type":"Polygon","coordinates":[[[5.3698,43.7465],[5.9098,43.5965],[6.1098,43.2965],[5.9098,42.9965],[5.3698,42.8465],[4.8298,42.9965],[4.6298,43.2965],[4.8298,43.5965],[5.3698,43.7465]]]}', NOW(), '{"node":"Marseille","radius_km":50}'),
    (444444, '{"type":"Polygon","coordinates":[[[1.4442,44.0547],[1.9842,43.9047],[2.1842,43.6047],[1.9842,43.3047],[1.4442,43.1547],[0.9042,43.3047],[0.7042,43.6047],[0.9042,43.9047],[1.4442,44.0547]]]}', NOW(), '{"node":"Toulouse","radius_km":50}'),
    (555555, '{"type":"Polygon","coordinates":[[[2.1301,49.2514],[2.6701,49.1014],[2.8701,48.8014],[2.6701,48.5014],[2.1301,48.3514],[1.5901,48.5014],[1.3901,48.8014],[1.5901,49.1014],[2.1301,49.2514]]]}', NOW(), '{"node":"Versailles","radius_km":50}')
    ON CONFLICT ("NodeId") DO UPDATE
                                  SET "GeoJSON" = EXCLUDED."GeoJSON",
                                  "CalculatedAt" = EXCLUDED."CalculatedAt",
                                  "Parameters" = EXCLUDED."Parameters";


-- docker cp .\init-sample-data.sql docker-database-1:/tmp/init-sample-data.sql
-- docker exec docker-database-1 psql -U postgres -f /tmp/init-sample-data.sql