using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using VulnerableMVC.Data;
using VulnerableMVC.Models;

namespace VulnerableMVC.Controllers;

public class HomeController : Controller
{
    private readonly MvcDbContext _db;

    public HomeController(MvcDbContext db) => _db = db;

    public async Task<IActionResult> Index()
    {
        var posts = await _db.BlogPosts.ToListAsync();
        return View(posts);
    }

    /// <summary>
    /// VULNERABILITY (A03 - XSS): Reflected XSS via search query.
    /// The query parameter is reflected back to the page without encoding.
    /// ZAP will detect this during its active scan.
    /// </summary>
    public async Task<IActionResult> Search(string query)
    {
        // VULNERABILITY (A03): Reflected XSS – query passed directly to ViewBag
        ViewBag.Query = query;  // Not encoded in the view → XSS

        // VULNERABILITY (A03): SQL Injection in search
        var results = await _db.BlogPosts
            .FromSqlRaw($"SELECT * FROM BlogPosts WHERE Title LIKE '%{query}%' OR Content LIKE '%{query}%'")
            .ToListAsync();

        return View(results);
    }

    /// <summary>
    /// VULNERABILITY (A03 - XSS): Stored XSS via comments.
    /// Comments are stored and later rendered without encoding.
    /// </summary>
    [HttpPost]
    public async Task<IActionResult> AddComment(int postId, string author, string content)
    {
        // VULNERABILITY: No CSRF token validation (missing [ValidateAntiForgeryToken])
        // VULNERABILITY (A04): No input validation or sanitization
        var comment = new Comment
        {
            BlogPostId = postId,
            Author = author,
            Content = content  // Stored XSS – will be rendered raw in view
        };

        _db.Comments.Add(comment);
        await _db.SaveChangesAsync();

        return RedirectToAction("Post", new { id = postId });
    }

    public async Task<IActionResult> Post(int id)
    {
        var post = await _db.BlogPosts.FindAsync(id);
        if (post == null) return NotFound();

        var comments = await _db.Comments.Where(c => c.BlogPostId == id).ToListAsync();
        ViewBag.Post = post;
        ViewBag.Comments = comments;

        return View();
    }

    /// <summary>
    /// VULNERABILITY (A10): Open redirect – ZAP will detect this.
    /// </summary>
    public IActionResult Redirect(string url)
    {
        // VULNERABILITY (A10): Open redirect without URL validation
        return Redirect(url);
    }

    /// <summary>
    /// VULNERABILITY (A05): Error page leaks stack trace.
    /// </summary>
    public IActionResult Error()
    {
        throw new Exception("Intentional error to leak stack trace information");
    }
}
