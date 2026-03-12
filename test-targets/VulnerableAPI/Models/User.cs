namespace VulnerableAPI.Models;

public class User
{
    public int Id { get; set; }
    public string Username { get; set; } = string.Empty;

    // VULNERABILITY (A02/A07): Password stored as plain text, no hashing
    public string Password { get; set; } = string.Empty;

    public string Email { get; set; } = string.Empty;
    public string Role { get; set; } = "User";

    // VULNERABILITY (A02): Sensitive PII stored without encryption
    public string CreditCard { get; set; } = string.Empty;

    // VULNERABILITY (A02): SSN stored in plain text
    public string? SocialSecurityNumber { get; set; }
}
