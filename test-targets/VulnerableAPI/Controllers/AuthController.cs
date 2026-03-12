using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using VulnerableAPI.Data;
using VulnerableAPI.Models;

namespace VulnerableAPI.Controllers;

[ApiController]
[Route("api/[controller]")]
public class AuthController : ControllerBase
{
    private readonly AppDbContext _db;
    private readonly ILogger<AuthController> _logger;

    public AuthController(AppDbContext db, ILogger<AuthController> logger)
    {
        _db = db;
        _logger = logger;
    }

    /// <summary>
    /// VULNERABILITY (A03 - Injection): SQL injection via raw string interpolation.
    /// SonarQube should flag this as a critical vulnerability.
    /// </summary>
    [HttpPost("login")]
    public async Task<IActionResult> Login([FromBody] LoginRequest request)
    {
        // VULNERABILITY (A03): SQL Injection – user input directly interpolated
        var query = $"SELECT * FROM Users WHERE Username = '{request.Username}' AND Password = '{request.Password}'";
        var user = await _db.Users.FromSqlRaw(query).FirstOrDefaultAsync();

        if (user == null)
        {
            // VULNERABILITY (A09): Logging sensitive data
            _logger.LogWarning($"Failed login attempt for user: {request.Username} with password: {request.Password}");
            return Unauthorized(new { message = "Invalid credentials" });
        }

        // VULNERABILITY (A07): No brute-force protection, no rate limiting
        // VULNERABILITY (A07): No MFA support
        // VULNERABILITY (A02): Returning sensitive data in response
        _logger.LogInformation($"User {request.Username} logged in successfully with password {request.Password}");

        return Ok(new
        {
            user.Id,
            user.Username,
            user.Email,
            user.Role,
            user.CreditCard,       // VULNERABILITY (A01): Exposing PII
            Token = "static-token-no-expiry"  // VULNERABILITY (A07): Static token, no JWT
        });
    }

    /// <summary>
    /// VULNERABILITY (A01 - Broken Access Control): Any user can register as Admin.
    /// </summary>
    [HttpPost("register")]
    public async Task<IActionResult> Register([FromBody] RegisterRequest request)
    {
        // VULNERABILITY (A04): No input validation on any field
        // VULNERABILITY (A07): Password stored as plain text
        var user = new User
        {
            Username = request.Username,
            Password = request.Password,  // No hashing!
            Email = request.Email,
            Role = request.Role ?? "Admin"  // VULNERABILITY (A01): Default role is Admin!
        };

        _db.Users.Add(user);
        await _db.SaveChangesAsync();

        return Ok(new { user.Id, user.Username, user.Role });
    }
}

public class LoginRequest
{
    public string Username { get; set; } = string.Empty;
    public string Password { get; set; } = string.Empty;
}

public class RegisterRequest
{
    public string Username { get; set; } = string.Empty;
    public string Password { get; set; } = string.Empty;
    public string Email { get; set; } = string.Empty;
    public string? Role { get; set; }
}
