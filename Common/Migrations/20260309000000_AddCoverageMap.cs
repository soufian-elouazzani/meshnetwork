using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Common.Migrations
{
    /// <inheritdoc />
    public partial class AddCoverageMap : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            // Table already created manually in PostgreSQL.
            // This migration registers it in EF Core's migration history
            // so the model snapshot stays in sync.
            migrationBuilder.Sql(@"
                CREATE TABLE IF NOT EXISTS ""CoverageMaps"" (
                    ""NodeId"" bigint NOT NULL,
                    ""GeoJSON"" jsonb NOT NULL,
                    ""CalculatedAt"" timestamp with time zone NOT NULL DEFAULT now(),
                    ""Parameters"" jsonb,
                    CONSTRAINT ""PK_CoverageMaps"" PRIMARY KEY (""NodeId""),
                    CONSTRAINT ""FK_CoverageMaps_Nodes_NodeId""
                        FOREIGN KEY (""NodeId"")
                        REFERENCES ""Nodes"" (""Id"")
                        ON DELETE CASCADE
                );
            ");

            migrationBuilder.Sql(@"
                CREATE INDEX IF NOT EXISTS ""IX_CoverageMaps_CalculatedAt""
                ON ""CoverageMaps"" (""CalculatedAt"");
            ");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(name: "CoverageMaps");
        }
    }
}