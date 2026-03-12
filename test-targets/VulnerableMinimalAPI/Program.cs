using Microsoft.EntityFrameworkCore;
using System.Data.SqlClient;
using System.Diagnostics;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Xml;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

// VULNERABILITY (A05): In-memory database with hardcoded connection info
builder.Services.AddDbContext<StoreDb>(opt => opt.UseSqlite("Data Source=store.db"));

var app = builder.Build();
app.UseSwagger();
app.UseSwaggerUI();

// Seed
using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<StoreDb>();
    db.Database.EnsureCreated();
    if (!db.Customers.Any())
    {
        db.Customers.AddRange(
            new Customer { Name = "Alice", Email = "alice@example.com", Password = "alice123", Balance = 1000m },
            new Customer { Name = "Bob", Email = "bob@example.com", Password = "bob456", Balance = 500m }
        );
        db.Items.AddRange(
            new Item { Name = "Widget", Price = 29.99m },
            new Item { Name = "Gadget", Price = 149.99m }
        );
        db.SaveChanges();
    }
}

// ─── VULNERABILITY ENDPOINTS ─────────────────────────────────────────────────

// A03: SQL Injection in login
app.MapPost("/api/login", async (LoginDto dto, StoreDb db) =>
{
    // VULNERABILITY (A03): SQL Injection via string interpolation
    var sql = $"SELECT * FROM Customers WHERE Email = '{dto.Email}' AND Password = '{dto.Password}'";
    var customer = await db.Customers.FromSqlRaw(sql).FirstOrDefaultAsync();

    if (customer == null)
        return Results.Unauthorized();

    // VULNERABILITY (A02): Returning password in response
    return Results.Ok(new { customer.Id, customer.Name, customer.Email, customer.Password, customer.Balance });
});

// A01: No authentication on any endpoint
app.MapGet("/api/customers", async (StoreDb db) =>
{
    // VULNERABILITY (A01): All customer data exposed without auth, including passwords
    return Results.Ok(await db.Customers.ToListAsync());
});

// A01: IDOR – access any customer by ID
app.MapGet("/api/customers/{id}", async (int id, StoreDb db) =>
{
    var customer = await db.Customers.FindAsync(id);
    return customer == null ? Results.NotFound() : Results.Ok(customer);
});

// A03: SQL Injection in search
app.MapGet("/api/items/search", async (string q, StoreDb db) =>
{
    // VULNERABILITY (A03): SQL injection
    var items = await db.Items.FromSqlRaw($"SELECT * FROM Items WHERE Name LIKE '%{q}%'").ToListAsync();
    return Results.Ok(items);
});

// A01: Transfer money without authentication or authorization
app.MapPost("/api/transfer", async (TransferDto dto, StoreDb db) =>
{
    // VULNERABILITY (A01): No auth check – anyone can transfer from any account
    // VULNERABILITY (A04): No validation on amount (negative transfers = steal money)
    var sender = await db.Customers.FindAsync(dto.FromId);
    var receiver = await db.Customers.FindAsync(dto.ToId);

    if (sender == null || receiver == null) return Results.NotFound();

    // VULNERABILITY (A04): No check for negative amounts or overdrafts
    sender.Balance -= dto.Amount;
    receiver.Balance += dto.Amount;
    await db.SaveChangesAsync();

    return Results.Ok(new { sender = new { sender.Id, sender.Balance }, receiver = new { receiver.Id, receiver.Balance } });
});

// A10: SSRF
app.MapGet("/api/proxy", async (string url) =>
{
    // VULNERABILITY (A10): Server-Side Request Forgery
    using var client = new HttpClient();
    var response = await client.GetStringAsync(url);
    return Results.Ok(new { url, body = response });
});

// A03: Command Injection
app.MapGet("/api/ping", (string host) =>
{
    // VULNERABILITY (A03): OS Command Injection
    var psi = new ProcessStartInfo("cmd.exe", $"/c ping -n 2 {host}")
    {
        RedirectStandardOutput = true,
        UseShellExecute = false
    };
    var process = Process.Start(psi)!;
    var output = process.StandardOutput.ReadToEnd();
    process.WaitForExit();
    return Results.Ok(new { host, output });
});

// A01: Path Traversal
app.MapGet("/api/download", (string file) =>
{
    // VULNERABILITY (A01): Path traversal – no sanitization
    var fullPath = Path.Combine(Directory.GetCurrentDirectory(), file);
    if (!System.IO.File.Exists(fullPath))
        return Results.NotFound();
    return Results.File(fullPath);
});

// A02: Weak crypto
app.MapPost("/api/hash", (HashDto dto) =>
{
    // VULNERABILITY (A02): MD5 hashing
    using var md5 = MD5.Create();
    var hash = md5.ComputeHash(Encoding.UTF8.GetBytes(dto.Input));
    return Results.Ok(new { algorithm = "MD5", hash = Convert.ToHexString(hash) });
});

// A02: Hardcoded secrets endpoint
app.MapGet("/api/config", () =>
{
    // VULNERABILITY (A02 + A05): Exposing secrets and internal config
    return Results.Ok(new
    {
        DbConnectionString = "Server=prod-db.internal;Database=store;User=sa;Password=EXAMPLE_password",
        StripeApiKey = "sk_test_EXAMPLE_DO_NOT_USE_IN_PRODUCTION",
        JwtSecret = "INSECURE_JWT_SECRET_EXAMPLE_DO_NOT_USE",
        AwsAccessKey = "AKIAIOSFODNN7EXAMPLE",
        AwsSecretKey = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        RedisPassword = "EXAMPLE_redis_password",
    });
});

// A08: XXE
app.MapPost("/api/parse-xml", (HttpContext ctx) =>
{
    using var reader = new StreamReader(ctx.Request.Body);
    var xml = reader.ReadToEndAsync().Result;

    // VULNERABILITY (A08): XXE – external entity resolution enabled
    var settings = new XmlReaderSettings
    {
        DtdProcessing = DtdProcessing.Parse,
        XmlResolver = new XmlUrlResolver()
    };

    using var xmlReader = XmlReader.Create(new StringReader(xml), settings);
    var doc = new XmlDocument();
    doc.Load(xmlReader);
    return Results.Ok(new { parsed = doc.OuterXml });
});

// A05: ReDoS – regex denial of service
app.MapGet("/api/validate-email", (string email) =>
{
    // VULNERABILITY (A04/A05): ReDoS-vulnerable regex pattern
    var pattern = @"^([a-zA-Z0-9]+\.)+[a-zA-Z0-9]+@([a-zA-Z0-9]+\.)+[a-zA-Z]{2,}$";
    var isValid = Regex.IsMatch(email, pattern, RegexOptions.None, TimeSpan.FromSeconds(30));
    return Results.Ok(new { email, valid = isValid });
});

// A09: Logging sensitive data
app.MapPost("/api/checkout", async (CheckoutDto dto, StoreDb db, ILogger<Program> logger) =>
{
    // VULNERABILITY (A09): Logging credit card number and CVV
    logger.LogInformation($"Checkout: customer={dto.CustomerId}, card={dto.CreditCard}, cvv={dto.Cvv}, amount={dto.Amount}");

    var customer = await db.Customers.FindAsync(dto.CustomerId);
    if (customer == null) return Results.NotFound();

    customer.Balance -= dto.Amount;
    await db.SaveChangesAsync();

    return Results.Ok(new { message = "Payment processed", remaining = customer.Balance });
});

app.Run();

// ─── Models ──────────────────────────────────────────────────────────────────

class StoreDb : DbContext
{
    public StoreDb(DbContextOptions<StoreDb> options) : base(options) { }
    public DbSet<Customer> Customers => Set<Customer>();
    public DbSet<Item> Items => Set<Item>();
}

class Customer
{
    public int Id { get; set; }
    public string Name { get; set; } = "";
    public string Email { get; set; } = "";
    public string Password { get; set; } = "";   // VULNERABILITY: Plain text
    public decimal Balance { get; set; }
}

class Item
{
    public int Id { get; set; }
    public string Name { get; set; } = "";
    public decimal Price { get; set; }
}

record LoginDto(string Email, string Password);
record TransferDto(int FromId, int ToId, decimal Amount);
record HashDto(string Input);
record CheckoutDto(int CustomerId, string CreditCard, string Cvv, decimal Amount);
