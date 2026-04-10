using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using ktcards.Server.Data;
using ktcards.Server.Models;

namespace ktcards.Server.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    public class TeamsController(AppDbContext db, IWebHostEnvironment env) : ControllerBase
    {
        [HttpGet]
        public async Task<IActionResult> GetAll()
        {
            var teams = await db.Teams
                .OrderBy(t => t.Id)
                .Select(t => new
                {
                    t.Id,
                    t.Name,
                    t.LogoPath,
                    t.SeasonId
                })
                .ToListAsync();
            return Ok(teams);
        }

        [HttpPost]
        [Consumes("multipart/form-data")]
        public async Task<IActionResult> Create([FromForm] TeamFormDto dto)
        {
            if (string.IsNullOrWhiteSpace(dto.Name))
                return BadRequest("Name is required.");
            if (!await db.Seasons.AnyAsync(s => s.Id == dto.SeasonId))
                return BadRequest("Season not found.");

            string? logoPath = null;
            if (dto.Logo is not null && dto.Logo.Length > 0)
            {
                var uploadsDir = Path.Combine(env.WebRootPath, "uploads");
                Directory.CreateDirectory(uploadsDir);
                var ext = Path.GetExtension(dto.Logo.FileName);
                var fileName = $"{Guid.NewGuid()}{ext}";
                var filePath = Path.Combine(uploadsDir, fileName);
                await using var stream = System.IO.File.Create(filePath);
                await dto.Logo.CopyToAsync(stream);
                logoPath = $"/uploads/{fileName}";
            }

            var team = new Team
            {
                Name = dto.Name.Trim(),
                SeasonId = dto.SeasonId,
                LogoPath = logoPath
            };
            db.Teams.Add(team);
            await db.SaveChangesAsync();
            return Ok(new { team.Id, team.Name, team.LogoPath, team.SeasonId });
        }

        [HttpDelete("{id:int}")]
        public async Task<IActionResult> Delete(int id)
        {
            var team = await db.Teams.FindAsync(id);
            if (team is null) return NotFound();
            DeleteLogo(team.LogoPath);
            db.Teams.Remove(team);
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

    public record TeamFormDto(string Name, int SeasonId, IFormFile? Logo);
}
