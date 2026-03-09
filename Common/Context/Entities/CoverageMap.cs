using System.Text.Json;

namespace Common.Context.Entities;

public class CoverageMap
{
    /// <summary>
    /// FK → Nodes.Id (also PK : one coverage per node)
    /// </summary>
    public long NodeId { get; set; }
    public virtual Node Node { get; set; } = null!;

    /// <summary>
    /// GeoJSON stored as raw JSON (Polygon or MultiPolygon)
    /// </summary>
    public required JsonDocument GeoJson { get; set; }

    public DateTime CalculatedAt { get; set; } = DateTime.UtcNow;

    /// <summary>
    /// Optional metadata : radius_m, snr_threshold, algorithm …
    /// </summary>
    public JsonDocument? Parameters { get; set; }
}