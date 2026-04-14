using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using System.Collections.Concurrent;
using System.Text;
using System.Text.Json;
using ktcards.Server.Data;
using ktcards.Server.Filters;
using ktcards.Server.Models;

namespace ktcards.Server.Controllers
{
    [ApiController]
    [Route("api/teams/{teamId:int}/cards")]
    [ServiceFilter(typeof(AntiforgeryValidationFilter))]
    public class CardsController(AppDbContext db, IConfiguration config, IHttpClientFactory httpClientFactory) : ControllerBase
    {
        private static readonly JsonSerializerOptions JsonOptions = new()
        {
            PropertyNameCaseInsensitive = true
        };

        // Per-team semaphores prevent concurrent imports from causing duplicate cards.
        private static readonly ConcurrentDictionary<int, SemaphoreSlim> ImportLocks = new();

        // GET /api/teams/{teamId}/cards — return all cards for a team
        [HttpGet]
        public async Task<IActionResult> GetCards(int teamId)
        {
            if (!await db.Teams.AnyAsync(t => t.Id == teamId))
                return NotFound("Team not found.");

            var operatives = await db.Operatives
                .Where(o => o.TeamId == teamId)
                .Include(o => o.Abilities)
                .Include(o => o.Attacks)
                .ToListAsync();

            var factionRules = await db.FactionRules.Where(r => r.TeamId == teamId).ToListAsync();
            var markerTokens = await db.MarkerTokens.Where(m => m.TeamId == teamId).ToListAsync();
            var strategyPloys = await db.StrategyPloys.Where(p => p.TeamId == teamId).ToListAsync();
            var firefightPloys = await db.FirefightPloys.Where(p => p.TeamId == teamId).ToListAsync();
            var factionEquipment = await db.FactionEquipments.Where(e => e.TeamId == teamId).ToListAsync();

            return Ok(new
            {
                operatives,
                factionRules,
                markerTokens,
                strategyPloys,
                firefightPloys,
                factionEquipment
            });
        }

        // POST /api/teams/{teamId}/cards/import — import cards from the .bd file
        [HttpPost("import")]
        [AdminAuthorize]
        public async Task<IActionResult> ImportCards(int teamId)
        {
            var team = await db.Teams.FindAsync(teamId);
            if (team is null)
                return NotFound("Team not found.");

            // Acquire per-team lock to prevent race conditions when two concurrent
            // requests both delete-then-insert cards for the same team.
            var semaphore = ImportLocks.GetOrAdd(teamId, _ => new SemaphoreSlim(1, 1));
            if (!await semaphore.WaitAsync(TimeSpan.Zero))
                return Conflict("An import is already in progress for this team.");

            try
            {
                var baseUrl = config["DatacardsBaseUrl"]
                    ?? "https://api.github.com/repos/Shooshpanius/ktcards/contents/datacards";
                var datacardsRef = config["DatacardsRef"] ?? "master";
                var apiUrl = $"{baseUrl.TrimEnd('/')}/{Uri.EscapeDataString(team.Name)}.bd?ref={datacardsRef}";

                string json;
                try
                {
                    var httpClient = httpClientFactory.CreateClient("github");
                    var request = new HttpRequestMessage(HttpMethod.Get, apiUrl);
                    request.Headers.Add("User-Agent", "ktcards");
                    var gitHubToken = config["GitHubToken"];
                    if (!string.IsNullOrWhiteSpace(gitHubToken))
                        request.Headers.Add("Authorization", $"Bearer {gitHubToken}");

                    var response = await httpClient.SendAsync(request);
                    if (!response.IsSuccessStatusCode)
                        return NotFound($"File '{team.Name}.bd' not found in the datacards repository.");

                    var apiJson = await response.Content.ReadAsStringAsync();
                    using var doc = JsonDocument.Parse(apiJson);
                    var b64 = doc.RootElement.GetProperty("content").GetString()
                        ?? throw new InvalidOperationException("No content field in GitHub API response.");
                    json = Encoding.UTF8.GetString(Convert.FromBase64String(
                        b64.Replace("\n", "").Replace("\r", "")));
                }
                catch (HttpRequestException ex)
                {
                    return StatusCode(502, $"Failed to fetch '{team.Name}.bd' from repository: {ex.Message}");
                }

                TeamDataCard? data;
                try
                {
                    data = JsonSerializer.Deserialize<TeamDataCard>(json, JsonOptions);
                }
                catch (JsonException ex)
                {
                    return BadRequest($"Failed to parse '{team.Name}.bd': {ex.Message}");
                }

                if (data is null)
                    return BadRequest($"'{team.Name}.bd' is empty or invalid.");

                // Remove existing cards for this team (cascade delete handles operative children)
                db.Operatives.RemoveRange(db.Operatives.Where(o => o.TeamId == teamId));
                db.FactionRules.RemoveRange(db.FactionRules.Where(r => r.TeamId == teamId));
                db.MarkerTokens.RemoveRange(db.MarkerTokens.Where(m => m.TeamId == teamId));
                db.StrategyPloys.RemoveRange(db.StrategyPloys.Where(p => p.TeamId == teamId));
                db.FirefightPloys.RemoveRange(db.FirefightPloys.Where(p => p.TeamId == teamId));
                db.FactionEquipments.RemoveRange(db.FactionEquipments.Where(e => e.TeamId == teamId));
                await db.SaveChangesAsync();

                // Insert new cards
                if (data.Operatives is not null)
                {
                    foreach (var op in data.Operatives)
                    {
                        var operative = new Operative
                        {
                            TeamId = teamId,
                            Name = op.Name ?? string.Empty,
                            Keywords = op.Keywords is not null ? string.Join(", ", op.Keywords) : null,
                            Movement = op.Movement,
                            ActionPointLimit = op.ActionPointLimit,
                            GroupActivations = op.GroupActivations,
                            Defence = op.Defence,
                            Save = op.Save,
                            Wounds = op.Wounds,
                            Notes = op.Notes,
                            Abilities = op.Abilities?.Select(a => new OperativeAbility
                            {
                                Name = a.Name ?? string.Empty,
                                Description = a.Description ?? string.Empty
                            }).ToList() ?? [],
                            Attacks = op.Attacks?.Select(a => new OperativeAttack
                            {
                                Name = a.Name ?? string.Empty,
                                AttackType = a.Type ?? string.Empty,
                                Attacks = a.Attacks,
                                HitSkill = a.HitSkill,
                                Damage = a.Damage ?? string.Empty,
                                CriticalDamage = a.CriticalDamage ?? string.Empty,
                                SpecialRules = a.SpecialRules
                            }).ToList() ?? []
                        };
                        db.Operatives.Add(operative);
                    }
                }

                if (data.FactionRules is not null)
                    db.FactionRules.AddRange(data.FactionRules.Select(r => new FactionRule
                    {
                        TeamId = teamId,
                        Name = r.Name ?? string.Empty,
                        Description = r.Description ?? string.Empty
                    }));

                if (data.MarkersTokens is not null)
                    db.MarkerTokens.AddRange(data.MarkersTokens.Select(m => new MarkerToken
                    {
                        TeamId = teamId,
                        Name = m.Name ?? string.Empty,
                        Description = m.Description ?? string.Empty
                    }));

                if (data.StrategyPloys is not null)
                    db.StrategyPloys.AddRange(data.StrategyPloys.Select(p => new StrategyPloy
                    {
                        TeamId = teamId,
                        Name = p.Name ?? string.Empty,
                        CpCost = p.CpCost,
                        Description = p.Description ?? string.Empty
                    }));

                if (data.FirefightPloys is not null)
                    db.FirefightPloys.AddRange(data.FirefightPloys.Select(p => new FirefightPloy
                    {
                        TeamId = teamId,
                        Name = p.Name ?? string.Empty,
                        CpCost = p.CpCost,
                        Description = p.Description ?? string.Empty
                    }));

                if (data.FactionEquipment is not null)
                    db.FactionEquipments.AddRange(data.FactionEquipment.Select(e => new FactionEquipment
                    {
                        TeamId = teamId,
                        Name = e.Name ?? string.Empty,
                        EpCost = e.EpCost,
                        Description = e.Description ?? string.Empty,
                        Restrictions = e.Restrictions
                    }));

                await db.SaveChangesAsync();
                return Ok(new { message = $"Cards for '{team.Name}' imported successfully." });
            }
            finally
            {
                semaphore.Release();
            }
        }
    }

    // DTO types matching the .bd JSON file format
    public record TeamDataCard(
        string? TeamName,
        List<OperativeDto>? Operatives,
        List<NameDescDto>? FactionRules,
        List<NameDescDto>? MarkersTokens,
        List<PloyDto>? StrategyPloys,
        List<PloyDto>? FirefightPloys,
        List<EquipmentDto>? FactionEquipment
    );

    public record OperativeDto(
        string? Name,
        List<string>? Keywords,
        string? Movement,
        int ActionPointLimit,
        int GroupActivations,
        int Defence,
        int Save,
        int Wounds,
        string? Notes,
        List<NameDescDto>? Abilities,
        List<AttackDto>? Attacks
    );

    public record AttackDto(
        string? Name,
        string? Type,
        int Attacks,
        int HitSkill,
        string? Damage,
        string? CriticalDamage,
        string? SpecialRules
    );

    public record NameDescDto(string? Name, string? Description);

    public record PloyDto(string? Name, int CpCost, string? Description);

    public record EquipmentDto(string? Name, int EpCost, string? Description, string? Restrictions);
}
