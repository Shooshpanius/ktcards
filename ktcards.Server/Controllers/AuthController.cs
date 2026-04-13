using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.RateLimiting;
using System.Security.Cryptography;
using System.Text;
using ktcards.Server.Filters;
using ktcards.Server.Helpers;
namespace ktcards.Server.Controllers
{
    [ApiController]
    [Route("api/auth")]
    public class AuthController(
        IConfiguration config,
        AdminTokenService tokenService) : ControllerBase
    {
        private const string CookieName = "admin_session";

        [HttpPost("login")]
        [EnableRateLimiting("login")]
        public IActionResult Login([FromBody] LoginDto dto)
        {
            var expectedPassword = config["AdminPassword"] ?? string.Empty;
            var inputBytes = Encoding.UTF8.GetBytes(dto.Password ?? string.Empty);
            var expectedBytes = Encoding.UTF8.GetBytes(expectedPassword);

            // Constant-time comparison to prevent timing attacks
            if (expectedPassword.Length == 0 || !CryptographicOperations.FixedTimeEquals(inputBytes, expectedBytes))
                return Unauthorized("Неверный пароль.");

            var token = tokenService.CreateToken();
            Response.Cookies.Append(CookieName, token, new CookieOptions
            {
                HttpOnly = true,
                Secure = Request.IsHttps,
                SameSite = SameSiteMode.Lax,
                MaxAge = TimeSpan.FromHours(24),
                Path = "/"
            });
            return Ok();
        }

        [HttpPost("logout")]
        public IActionResult Logout()
        {
            if (Request.Cookies.ContainsKey(CookieName))
            {
                var token = Request.Cookies[CookieName];
                if (!string.IsNullOrEmpty(token))
                    tokenService.Invalidate(token);
            }
            Response.Cookies.Delete(CookieName, new CookieOptions
            {
                HttpOnly = true,
                Secure = Request.IsHttps,
                SameSite = SameSiteMode.Lax,
                Path = "/"
            });
            return NoContent();
        }

        [HttpGet("check")]
        [AdminAuthorize]
        public IActionResult Check() => Ok();
    }

    public record LoginDto(string? Password);
}
