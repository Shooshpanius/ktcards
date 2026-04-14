using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.RateLimiting;
using System.Security.Cryptography;
using System.Text;
using ktcards.Server.Helpers;

namespace ktcards.Server.Controllers
{
    [ApiController]
    [Route("api/auth")]
    public class AuthController(IConfiguration config, AdminTokenService tokenService, IWebHostEnvironment env) : ControllerBase
    {
        private const string CookieName = "admin_token";

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
                SameSite = SameSiteMode.Lax,
                Secure = !env.IsDevelopment(),
                Path = "/",
                MaxAge = TimeSpan.FromHours(24)
            });
            return Ok();
        }

        [HttpGet("check")]
        public IActionResult Check()
        {
            var token = Request.Cookies[CookieName] ?? string.Empty;
            if (!tokenService.Validate(token))
                return Unauthorized();
            return Ok();
        }

        [HttpPost("logout")]
        public IActionResult Logout()
        {
            var token = Request.Cookies[CookieName];
            if (token != null)
                tokenService.RevokeToken(token);
            Response.Cookies.Delete(CookieName, new CookieOptions { Path = "/" });
            return Ok();
        }
    }

    public record LoginDto(string? Password);
}
