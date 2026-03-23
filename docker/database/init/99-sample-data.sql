-- Insert sample nodes
INSERT INTO "Nodes" ("Id", "NodeId", "CreatedAt", "UpdatedAt", "LongName", "ShortName", "RegionCode", "Latitude", "Longitude", "LastSeen", "Ignored")
VALUES
    (111111, 111111, NOW(), NOW(), 'Paris Central', 'PCEN', 'Eu868', 48.8566, 2.3522, NOW(), false),
    (111112, 111112, NOW(), NOW(), 'Paris Montmartre', 'PMON', 'Eu868', 48.8867, 2.3431, NOW(), false),
    (111113, 111113, NOW(), NOW(), 'Paris La Defense', 'PLAD', 'Eu868', 48.8926, 2.2380, NOW(), false),
    (222221, 222221, NOW(), NOW(), 'Lyon Centre', 'LCEN', 'Eu868', 45.7640, 4.8357, NOW(), false),
    (333331, 333331, NOW(), NOW(), 'Marseille Centre', 'MCEN', 'Eu868', 43.2965, 5.3698, NOW(), false),
    (333332, 333332, NOW(), NOW(), 'Marseille Vieux Port', 'MVP', 'Eu868', 43.2962, 5.3752, NOW(), false),
    (444441, 444441, NOW(), NOW(), 'Toulouse Centre', 'TCEN', 'Eu868', 43.6047, 1.4442, NOW(), false),
    (555551, 555551, NOW(), NOW(), 'Bordeaux Centre', 'BCEN', 'Eu868', 44.8378, -0.5792, NOW(), false)
ON CONFLICT ("Id") DO NOTHING;



-- Show count
DO $$
DECLARE
    node_count INTEGER;
    coverage_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO node_count FROM "Nodes";
    SELECT COUNT(*) INTO coverage_count FROM "CoverageMaps";
    RAISE NOTICE 'Loaded % nodes and % coverage maps', node_count, coverage_count;
END $$;
