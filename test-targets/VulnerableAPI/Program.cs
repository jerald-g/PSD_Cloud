using Microsoft.EntityFrameworkCore;
using VulnerableAPI.Data;
using VulnerableAPI.Services;

var builder = WebApplication.CreateBuilder(args);

// VULNERABILITY: Debug mode left enabled, verbose errors exposed
builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseSqlite("Data Source=vulnerable.db"));

builder.Services.AddSingleton<CryptoService>();
builder.Services.AddSingleton<FileService>();

// VULNERABILITY (A05): No CORS restriction – wide open
builder.Services.AddCors(options =>
{
    options.AddDefaultPolicy(policy =>
    {
        policy.AllowAnyOrigin()
              .AllowAnyMethod()
              .AllowAnyHeader();
    });
});

var app = builder.Build();

// VULNERABILITY (A05): Swagger exposed in production
app.UseSwagger();
app.UseSwaggerUI();

// VULNERABILITY (A05): Detailed exception page in production
app.UseDeveloperExceptionPage();

app.UseCors();

// VULNERABILITY (A07): No authentication middleware configured
// app.UseAuthentication();
// app.UseAuthorization();

app.MapControllers();

// Seed the database
using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
    db.Database.EnsureCreated();
    DbSeeder.Seed(db);
}

app.Run();
