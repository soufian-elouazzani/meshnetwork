using System.Text.Json;

namespace MeshtasticMqttExplorer.Models;

public class CoverageMapDto
{
    public long NodeId { get; set; }
    public string? NodeName { get; set; }
    public double? Latitude { get; set; }
    public double? Longitude { get; set; }

    /// <summary>
    /// Raw GeoJSON object (Polygon / MultiPolygon) — sent as-is to Leaflet
    /// </summary>
    public JsonElement GeoJson { get; set; }

    /// <summary>
    /// Radius in metres derived from GeoJSON bounding box, used by the
    /// frontend to size the fallback circle when no polygon is available.
    /// </summary>
    public double? RadiusMeters { get; set; }

    public DateTime CalculatedAt { get; set; }

    public JsonElement? Parameters { get; set; }
}