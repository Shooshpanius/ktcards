using Microsoft.AspNetCore.Mvc;
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
            var expectedPassword = config["AdminPassword"];
            if (string.IsNullOrEmpty(expectedPassword) || dto.Password != expectedPassword)
                return Unauthorized("Неверный пароль.");

            var token = tokenService.CreateToken();
            return Ok(new { token });
        }
    }

    public record LoginDto(string Password);
}
