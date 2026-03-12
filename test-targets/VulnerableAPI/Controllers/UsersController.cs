using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using VulnerableAPI.Data;

namespace VulnerableAPI.Controllers;

[ApiController]
[Route("api/[controller]")]
public class UsersController : ControllerBase
{
    private readonly AppDbContext _db;

    public UsersController(AppDbContext db) => _db = db;

    /// <summary>
    /// VULNERABILITY (A01 - Broken Access Control): No auth required to list all users.
    /// VULNERABILITY (A02): Returns passwords and credit cards in plain text.
    /// </summary>
    [HttpGet]
    public async Task<IActionResult> GetAll()
    {
        // VULNERABILITY (A01): No authorization check – anyone can see all users
        var users = await _db.Users.ToListAsync();
        return Ok(users);  // Exposes passwords, credit cards, SSNs
    }

    /// <summary>
    /// VULNERABILITY (A01 - IDOR): User can access any other user's data by changing the ID.
    /// </summary>
    [HttpGet("{id}")]
    public async Task<IActionResult> GetById(int id)
    {
        // VULNERABILITY (A01): Insecure Direct Object Reference – no ownership check
        var user = await _db.Users.FindAsync(id);
        if (user == null) return NotFound();

        return Ok(new
        {
            user.Id,
            user.Username,
            user.Email,
            user.Password,         // VULNERABILITY (A02): Exposing password
            user.CreditCard,       // VULNERABILITY (A02): Exposing credit card
            user.SocialSecurityNumber, // VULNERABILITY (A02): Exposing SSN
            user.Role
        });
    }

    /// <summary>
    /// VULNERABILITY (A01): No auth, any user can delete any other user.
    /// </summary>
    [HttpDelete("{id}")]
    public async Task<IActionResult> Delete(int id)
    {
        // VULNERABILITY (A01): No authorization, no ownership verification
        var user = await _db.Users.FindAsync(id);
        if (user == null) return NotFound();

        _db.Users.Remove(user);
        await _db.SaveChangesAsync();
        return NoContent();
    }

    /// <summary>
    /// VULNERABILITY (A01 + A04): Mass assignment – user can set their own role.
    /// </summary>
    [HttpPut("{id}")]
    public async Task<IActionResult> Update(int id, [FromBody] dynamic updates)
    {
        var user = await _db.Users.FindAsync(id);
        if (user == null) return NotFound();

        // VULNERABILITY (A04/A08): Mass assignment via dynamic deserialization
        string json = System.Text.Json.JsonSerializer.Serialize(updates);
        var dict = System.Text.Json.JsonSerializer.Deserialize<Dictionary<string, string>>(json);

        if (dict == null) return BadRequest();

        if (dict.ContainsKey("Username")) user.Username = dict["Username"];
        if (dict.ContainsKey("Password")) user.Password = dict["Password"];  // Still no hashing
        if (dict.ContainsKey("Role")) user.Role = dict["Role"];  // Can escalate to Admin!
        if (dict.ContainsKey("Email")) user.Email = dict["Email"];

        await _db.SaveChangesAsync();
        return Ok(user);
    }
}
