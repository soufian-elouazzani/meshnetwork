using Common.Context;
using MeshtasticMqttExplorer.Models;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using System.Text.Json;

namespace MeshtasticMqttExplorer.Controllers;

/// <summary>
/// REST API that exposes coverage polygons stored in the CoverageMaps table.
/// Consumed by the CoverageMap Blazor page and directly by the Leaflet JS layer.
/// </summary>
[ApiController]
[Route("api/coverage")]
public class CoverageController(
    ILogger<CoverageController> logger,
    IDbContextFactory<DataContext> contextFactory) : AController(logger)
{
    /// <summary>GET /api/coverage/all — returns every coverage polygon with node metadata.</summary>
    [HttpGet("all")]
    public async Task<ActionResult<List<CoverageMapDto>>> GetAll()
    {
        await using var context = await contextFactory.CreateDbContextAsync();

        var rows = await context.CoverageMaps
            .Include(c => c.Node)
            .AsNoTracking()
            .ToListAsync();

        var dtos = rows.Select(c => new CoverageMapDto
        {
            NodeId        = c.NodeId,
            NodeName      = c.Node.AllNames ?? c.Node.LongName ?? c.Node.NodeId.ToString("X"),
            Latitude      = c.Node.Latitude,
            Longitude     = c.Node.Longitude,
            GeoJson       = c.GeoJson.RootElement.Clone(),
            RadiusMeters  = EstimateRadius(c.GeoJson.RootElement),
            CalculatedAt  = c.CalculatedAt,
            Parameters    = c.Parameters?.RootElement.Clone(),
        }).ToList();

        return Ok(dtos);
    }

    /// <summary>GET /api/coverage/{nodeId} — returns a single node's coverage.</summary>
    [HttpGet("{nodeId:long}")]
    public async Task<ActionResult<CoverageMapDto>> GetByNode(long nodeId)
    {
        await using var context = await contextFactory.CreateDbContextAsync();

        var c = await context.CoverageMaps
            .Include(c => c.Node)
            .AsNoTracking()
            .FirstOrDefaultAsync(c => c.NodeId == nodeId);

        if (c == null)
            return NotFound();

        return Ok(new CoverageMapDto
        {
            NodeId        = c.NodeId,
            NodeName      = c.Node.AllNames ?? c.Node.LongName ?? c.Node.NodeId.ToString("X"),
            Latitude      = c.Node.Latitude,
            Longitude     = c.Node.Longitude,
            GeoJson       = c.GeoJson.RootElement.Clone(),
            RadiusMeters  = EstimateRadius(c.GeoJson.RootElement),
            CalculatedAt  = c.CalculatedAt,
            Parameters    = c.Parameters?.RootElement.Clone(),
        });
    }

    // ── helpers ──────────────────────────────────────────────────────────────

    /// <summary>
    /// Estimates the coverage radius in metres from a GeoJSON bounding box.
    /// Works for Polygon and MultiPolygon geometries.
    /// Falls back to null when coordinates cannot be parsed.
    /// </summary>
    private static double? EstimateRadius(JsonElement geoJson)
    {
        try
        {
            var coords = CollectCoordinates(geoJson).ToList();
            if (coords.Count == 0) return null;

            var minLat = coords.Min(p => p.lat);
            var maxLat = coords.Max(p => p.lat);
            var minLon = coords.Min(p => p.lon);
            var maxLon = coords.Max(p => p.lon);

            var centerLat = (minLat + maxLat) / 2;
            var centerLon = (minLon + maxLon) / 2;

            // Distance from center to the farthest corner
            var radius = HaversineMeters(centerLat, centerLon, maxLat, maxLon);
            return Math.Round(radius);
        }
        catch
        {
            return null;
        }
    }

    private static IEnumerable<(double lat, double lon)> CollectCoordinates(JsonElement root)
    {
        if (!root.TryGetProperty("coordinates", out var coordsEl)) yield break;

        var type = root.TryGetProperty("type", out var t) ? t.GetString() : null;

        switch (type)
        {
            case "Polygon":
                foreach (var pt in FlattenRings(coordsEl)) yield return pt;
                break;
            case "MultiPolygon":
                foreach (var polygon in coordsEl.EnumerateArray())
                    foreach (var pt in FlattenRings(polygon)) yield return pt;
                break;
        }
    }

    private static IEnumerable<(double lat, double lon)> FlattenRings(JsonElement ringsEl)
    {
        foreach (var ring in ringsEl.EnumerateArray())
            foreach (var point in ring.EnumerateArray())
            {
                var arr = point.EnumerateArray().ToArray();
                if (arr.Length >= 2)
                    yield return (arr[1].GetDouble(), arr[0].GetDouble()); // GeoJSON: [lon, lat]
            }
    }

    private static double HaversineMeters(double lat1, double lon1, double lat2, double lon2)
    {
        const double R = 6_371_000; // Earth radius in metres
        var dLat = ToRad(lat2 - lat1);
        var dLon = ToRad(lon2 - lon1);
        var a = Math.Sin(dLat / 2) * Math.Sin(dLat / 2)
              + Math.Cos(ToRad(lat1)) * Math.Cos(ToRad(lat2))
              * Math.Sin(dLon / 2) * Math.Sin(dLon / 2);
        return R * 2 * Math.Atan2(Math.Sqrt(a), Math.Sqrt(1 - a));
    }

    private static double ToRad(double deg) => deg * Math.PI / 180;
}