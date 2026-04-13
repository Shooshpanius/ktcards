using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using ktcards.Server.Data;
using ktcards.Server.Filters;
using ktcards.Server.Helpers;
using ktcards.Server.Models;

namespace ktcards.Server.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    public class TeamsController(AppDbContext db, IWebHostEnvironment env) : ControllerBase
    {
        private static readonly HashSet<string> AllowedExtensions = new(StringComparer.OrdinalIgnoreCase)
        {
            ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"
        };

        private static readonly HashSet<string> AllowedContentTypes = new(StringComparer.OrdinalIgnoreCase)
        {
            "image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml"
        };

        private const long MaxLogoSize = 5 * 1024 * 1024; // 5 MB
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
        [AdminAuthorize]
        public async Task<IActionResult> Create([FromForm] TeamFormDto dto)
        {
            if (string.IsNullOrWhiteSpace(dto.Name))
                return BadRequest("Name is required.");
            if (!await db.Seasons.AnyAsync(s => s.Id == dto.SeasonId))
                return BadRequest("Season not found.");

            string? logoPath = null;
            if (dto.Logo is not null && dto.Logo.Length > 0)
            {
                if (dto.Logo.Length > MaxLogoSize)
                    return BadRequest("Размер логотипа не должен превышать 5 МБ.");

                var ext = Path.GetExtension(dto.Logo.FileName);
                if (!AllowedExtensions.Contains(ext))
                    return BadRequest("Допустимые форматы логотипа: JPG, PNG, GIF, WebP, SVG.");

                if (!AllowedContentTypes.Contains(dto.Logo.ContentType))
                    return BadRequest("Недопустимый тип содержимого файла логотипа.");

                var uploadsDir = Path.Combine(env.WebRootPath, "uploads");
                Directory.CreateDirectory(uploadsDir);
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
        [AdminAuthorize]
        public async Task<IActionResult> Delete(int id)
        {
            var team = await db.Teams.FindAsync(id);
            if (team is null) return NotFound();
            FileHelper.DeleteLogo(team.LogoPath);
            db.Teams.Remove(team);
            await db.SaveChangesAsync();
            return NoContent();
        }
    }

    public record TeamFormDto(string Name, int SeasonId, IFormFile? Logo);
}
