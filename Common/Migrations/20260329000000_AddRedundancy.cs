using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Common.Migrations
{
    /// <inheritdoc />
    public partial class AddRedundancy : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            // Table already created by the redundancy service.
            // This migration registers it in EF Core's migration history
            // so the model snapshot stays in sync.
            migrationBuilder.Sql(@"
                CREATE TABLE IF NOT EXISTS ""Redundancy"" (
                    ""NodeId""       bigint                   NOT NULL,
                    ""Data""         jsonb                    NOT NULL,
                    ""CalculatedAt"" timestamp with time zone NOT NULL DEFAULT now(),
                    CONSTRAINT ""PK_Redundancy"" PRIMARY KEY (""NodeId"")
                );
            ");

            migrationBuilder.Sql(@"
                CREATE INDEX IF NOT EXISTS ""IX_Redundancy_CalculatedAt""
                ON ""Redundancy"" (""CalculatedAt"");
            ");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(name: "Redundancy");
        }
    }
}