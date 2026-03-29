using System.Text.Json;

namespace Common.Context.Entities;

public class Redundancy
{
    /// <summary>
    /// PK : one redundancy row per node
    /// </summary>
    public long NodeId { get; set; }

    /// <summary>
    /// Redundancy data stored as raw JSONB
    /// Contains: color, nodeId, latitude, nodeName, longitude,
    /// totalScore, overlapCount, redundancyLevel, overlappingNodes
    /// </summary>
    public required JsonDocument Data { get; set; }

    public DateTime CalculatedAt { get; set; } = DateTime.UtcNow;
}