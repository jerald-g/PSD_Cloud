using Microsoft.EntityFrameworkCore;
using VulnerableMVC.Data;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllersWithViews();
builder.Services.AddDbContext<MvcDbContext>(options =>
    options.UseSqlite("Data Source=mvc_vulnerable.db"));

// VULNERABILITY (A05): No HTTPS redirection configured
// VULNERABILITY (A05): No security headers (HSTS, CSP, X-Frame-Options)

// VULNERABILITY (A07): Session with insecure cookie settings
builder.Services.AddSession(options =>
{
    options.Cookie.HttpOnly = false;   // VULNERABILITY: JavaScript can access cookie
    options.Cookie.SecurePolicy = CookieSecurePolicy.None; // VULNERABILITY: Sent over HTTP
    options.Cookie.SameSite = SameSiteMode.None; // VULNERABILITY: CSRF via cross-site
    options.IdleTimeout = TimeSpan.FromDays(365); // VULNERABILITY: Session never expires
});

var app = builder.Build();

app.UseDeveloperExceptionPage();  // VULNERABILITY (A05): Stack traces in production
app.UseStaticFiles();
app.UseRouting();
app.UseSession();

// VULNERABILITY (A07): No authentication/authorization middleware
// VULNERABILITY (A05): CSRF protection disabled by not using [ValidateAntiForgeryToken]

app.MapControllerRoute(
    name: "default",
    pattern: "{controller=Home}/{action=Index}/{id?}");

using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<MvcDbContext>();
    db.Database.EnsureCreated();
}

app.Run();
