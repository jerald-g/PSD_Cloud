using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using VulnerableAPI.Data;

namespace VulnerableAPI.Controllers;

[ApiController]
[Route("api/[controller]")]
public class ProductsController : ControllerBase
{
    private readonly AppDbContext _db;

    public ProductsController(AppDbContext db) => _db = db;

    /// <summary>
    /// VULNERABILITY (A03 - Injection): SQL injection in search query.
    /// </summary>
    [HttpGet("search")]
    public async Task<IActionResult> Search([FromQuery] string name)
    {
        // VULNERABILITY (A03): SQL Injection via string concatenation
        var query = $"SELECT * FROM Products WHERE Name LIKE '%{name}%'";
        var results = await _db.Products.FromSqlRaw(query).ToListAsync();
        return Ok(results);
    }

    [HttpGet]
    public async Task<IActionResult> GetAll()
    {
        return Ok(await _db.Products.ToListAsync());
    }

    [HttpGet("{id}")]
    public async Task<IActionResult> GetById(int id)
    {
        var product = await _db.Products.FindAsync(id);
        return product == null ? NotFound() : Ok(product);
    }

    /// <summary>
    /// VULNERABILITY (A04): No validation on price – can set negative prices.
    /// VULNERABILITY (A01): No authorization to create products.
    /// </summary>
    [HttpPost]
    public async Task<IActionResult> Create([FromBody] Models.Product product)
    {
        // VULNERABILITY (A04): No input validation – negative prices, zero stock, etc.
        _db.Products.Add(product);
        await _db.SaveChangesAsync();
        return CreatedAtAction(nameof(GetById), new { id = product.Id }, product);
    }
}
