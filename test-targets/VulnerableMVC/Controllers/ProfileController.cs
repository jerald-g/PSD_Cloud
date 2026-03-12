using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using VulnerableMVC.Data;
using VulnerableMVC.Models;

namespace VulnerableMVC.Controllers;

public class ProfileController : Controller
{
    private readonly MvcDbContext _db;

    public ProfileController(MvcDbContext db) => _db = db;

    /// <summary>
    /// VULNERABILITY (A01 - IDOR): Any user can view any profile by ID.
    /// </summary>
    public async Task<IActionResult> View(int id)
    {
        var profile = await _db.UserProfiles.FindAsync(id);
        return profile == null ? NotFound() : View(profile);
    }

    [HttpGet]
    public IActionResult Create() => View();

    /// <summary>
    /// VULNERABILITY (A03 - Stored XSS): Bio field rendered as raw HTML.
    /// VULNERABILITY: No CSRF protection.
    /// VULNERABILITY (A04): No input length or content validation.
    /// </summary>
    [HttpPost]
    public async Task<IActionResult> Create(UserProfile profile)
    {
        // No validation, no sanitization, no CSRF token
        _db.UserProfiles.Add(profile);
        await _db.SaveChangesAsync();
        return RedirectToAction("View", new { id = profile.Id });
    }

    /// <summary>
    /// VULNERABILITY (A03 - LDAP Injection): Simulated LDAP-style query.
    /// </summary>
    [HttpGet]
    public IActionResult Search(string username)
    {
        // VULNERABILITY (A03): LDAP injection pattern
        var ldapFilter = $"(&(uid={username})(objectClass=person))";
        ViewBag.Filter = ldapFilter;
        ViewBag.Username = username;
        return View();
    }
}
