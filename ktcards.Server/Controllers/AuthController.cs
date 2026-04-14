using Microsoft.AspNetCore.Mvc;
using System.Security.Cryptography;
using System.Text;
using ktcards.Server.Helpers;

namespace ktcards.Server.Controllers
{
    [ApiController]
    [Route("api/auth")]
    public class AuthController(IConfiguration config, AdminTokenService tokenService) : ControllerBase
    {
        [HttpPost("login")]
        public IActionResult Login([FromBody] LoginDto dto)
        {
            var expectedPassword = config["AdminPassword"] ?? string.Empty;
            var inputBytes = Encoding.UTF8.GetBytes(dto.Password ?? string.Empty);
            var expectedBytes = Encoding.UTF8.GetBytes(expectedPassword);

            // Constant-time comparison to prevent timing attacks
            if (expectedPassword.Length == 0 || !CryptographicOperations.FixedTimeEquals(inputBytes, expectedBytes))
                return Unauthorized("Неверный пароль.");

            var token = tokenService.CreateToken();
            return Ok(new { token });
        }
    }

    public record LoginDto(string? Password);
}
