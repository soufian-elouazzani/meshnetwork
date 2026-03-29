using Common.Context;
using MeshtasticMqttExplorer.Models;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace MeshtasticMqttExplorer.Controllers;

/// <summary>
/// REST API that exposes redundancy data stored in the Redundancy table.
/// </summary>
[ApiController]
[Route("api/redundancy")]
public class RedundancyController(
    ILogger<RedundancyController> logger,
    IDbContextFactory<DataContext> contextFactory) : AController(logger)
{
    /// <summary>GET /api/redundancy/all — returns redundancy info for all nodes.</summary>
    [HttpGet("all")]
    public async Task<ActionResult<List<RedundancyDto>>> GetAll()
    {
        await using var context = await contextFactory.CreateDbContextAsync();

        var rows = await context.Redundancies
            .AsNoTracking()
            .ToListAsync();

        return Ok(rows.Select(MapToDto).ToList());
    }

    /// <summary>GET /api/redundancy/{nodeId} — returns redundancy info for a single node.</summary>
    [HttpGet("{nodeId:long}")]
    public async Task<ActionResult<RedundancyDto>> GetByNode(long nodeId)
    {
        await using var context = await contextFactory.CreateDbContextAsync();

        var row = await context.Redundancies
            .AsNoTracking()
            .FirstOrDefaultAsync(r => r.NodeId == nodeId);

        if (row == null)
            return NotFound();

        return Ok(MapToDto(row));
    }

    private static RedundancyDto MapToDto(Common.Context.Entities.Redundancy r)
    {
        var data = r.Data.RootElement;

        var overlappingNodes = new List<OverlappingNodeDto>();

        if (data.TryGetProperty("overlappingNodes", out var overlapsEl))
        {
            foreach (var item in overlapsEl.EnumerateArray())
            {
                overlappingNodes.Add(new OverlappingNodeDto
                {
                    NodeId       = item.TryGetProperty("nodeId",       out var nid)   ? nid.GetInt64()    : 0,
                    NodeName     = item.TryGetProperty("nodeName",     out var nname) ? nname.GetString() : null,
                    OverlapScore = item.TryGetProperty("overlapScore",  out var score) ? score.GetDouble() : 0,
                });
            }
        }

        return new RedundancyDto
        {
            NodeId           = r.NodeId,
            NodeName         = data.TryGetProperty("nodeName",        out var name)    ? name.GetString()    : null,
            Latitude         = data.TryGetProperty("latitude",        out var lat)     ? lat.GetDouble()     : null,
            Longitude        = data.TryGetProperty("longitude",       out var lon)     ? lon.GetDouble()     : null,
            Color            = data.TryGetProperty("color",           out var color)   ? color.GetString()   : null,
            TotalScore       = data.TryGetProperty("totalScore",      out var ts)      ? ts.GetDouble()      : 0,
            OverlapCount     = data.TryGetProperty("overlapCount",    out var overlap) ? overlap.GetInt32()  : 0,
            RedundancyLevel  = data.TryGetProperty("redundancyLevel", out var level)   ? level.GetInt32()    : 1,
            OverlappingNodes = overlappingNodes,
            CalculatedAt     = r.CalculatedAt,
        };
    }
}