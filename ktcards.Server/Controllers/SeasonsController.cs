using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using ktcards.Server.Data;
using ktcards.Server.Models;

namespace ktcards.Server.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    public class SeasonsController(AppDbContext db) : ControllerBase
    {
        [HttpGet]
        public async Task<IActionResult> GetAll()
        {
            var seasons = await db.Seasons
                .Include(s => s.Teams)
                .OrderBy(s => s.Id)
                .Select(s => new
                {
                    s.Id,
                    s.Name,
                    Teams = s.Teams.Select(t => new
                    {
                        t.Id,
                        t.Name,
                        t.LogoPath,
                        t.SeasonId
                    })
                })
                .ToListAsync();
            return Ok(seasons);
        }

        [HttpPost]
        public async Task<IActionResult> Create([FromBody] SeasonDto dto)
        {
            if (string.IsNullOrWhiteSpace(dto.Name))
                return BadRequest("Name is required.");
            var season = new Season { Name = dto.Name.Trim() };
            db.Seasons.Add(season);
            await db.SaveChangesAsync();
            return Ok(new { season.Id, season.Name });
        }

        [HttpDelete("{id:int}")]
        public async Task<IActionResult> Delete(int id)
        {
            var season = await db.Seasons.Include(s => s.Teams).FirstOrDefaultAsync(s => s.Id == id);
            if (season is null) return NotFound();
            foreach (var team in season.Teams)
            {
                DeleteLogo(team.LogoPath);
            }
            db.Seasons.Remove(season);
            await db.SaveChangesAsync();
            return NoContent();
        }

        private static void DeleteLogo(string? logoPath)
        {
            if (string.IsNullOrEmpty(logoPath)) return;
            var filePath = Path.Combine(Directory.GetCurrentDirectory(), "wwwroot", logoPath.TrimStart('/'));
            if (System.IO.File.Exists(filePath))
                System.IO.File.Delete(filePath);
        }
    }

    public record SeasonDto(string Name);
}
