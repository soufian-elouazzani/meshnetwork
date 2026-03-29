using System.Text.Json;

namespace MeshtasticMqttExplorer.Models;

public class RedundancyDto
{
    public long NodeId { get; set; }
    public string? NodeName { get; set; }
    public double? Latitude { get; set; }
    public double? Longitude { get; set; }
    public string? Color { get; set; }
    public double TotalScore { get; set; }
    public int OverlapCount { get; set; }
    public int RedundancyLevel { get; set; }
    public List<OverlappingNodeDto> OverlappingNodes { get; set; } = [];
    public DateTime CalculatedAt { get; set; }
}

public class OverlappingNodeDto
{
    public long NodeId { get; set; }
    public string? NodeName { get; set; }
    public double OverlapScore { get; set; }
}