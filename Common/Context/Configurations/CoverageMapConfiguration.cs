using Common.Context.Entities;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

namespace Common.Context.Configurations;

public class CoverageMapConfiguration : IEntityTypeConfiguration<CoverageMap>
{
    public void Configure(EntityTypeBuilder<CoverageMap> builder)
    {
        // Map exactly to the existing table name
        builder.ToTable("CoverageMaps");

        // PK = NodeId (one coverage row per node)
        builder.HasKey(c => c.NodeId);

        // GeoJSON stored as jsonb
        builder.Property(c => c.GeoJson)
            .HasColumnName("GeoJSON")
            .HasColumnType("jsonb")
            .IsRequired();

        // Parameters stored as jsonb (optional)
        builder.Property(c => c.Parameters)
            .HasColumnName("Parameters")
            .HasColumnType("jsonb");

        builder.Property(c => c.CalculatedAt)
            .HasColumnName("CalculatedAt")
            .IsRequired();

        builder.HasIndex(c => c.CalculatedAt)
            .HasDatabaseName("IX_CoverageMaps_CalculatedAt");

        // FK → Nodes
        builder.HasOne(c => c.Node)
            .WithOne()
            .HasForeignKey<CoverageMap>(c => c.NodeId)
            .OnDelete(DeleteBehavior.Cascade)
            .HasConstraintName("FK_CoverageMaps_Nodes_NodeId");
    }
}