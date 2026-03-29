using Common.Context.Entities;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

namespace Common.Context.Configurations;

public class RedundancyConfiguration : IEntityTypeConfiguration<Redundancy>
{
    public void Configure(EntityTypeBuilder<Redundancy> builder)
    {
        builder.ToTable("Redundancy");

        // PK = NodeId (one row per node)
        builder.HasKey(r => r.NodeId);

        builder.Property(r => r.Data)
            .HasColumnName("Data")
            .HasColumnType("jsonb")
            .IsRequired();

        builder.Property(r => r.CalculatedAt)
            .HasColumnName("CalculatedAt")
            .IsRequired();

        builder.HasIndex(r => r.CalculatedAt)
            .HasDatabaseName("IX_Redundancy_CalculatedAt");

        // No FK to Nodes — the redundancy service manages this table independently
    }
}