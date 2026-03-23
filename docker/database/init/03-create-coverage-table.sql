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
