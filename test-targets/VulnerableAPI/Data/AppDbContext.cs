using Microsoft.EntityFrameworkCore;
using VulnerableAPI.Models;

namespace VulnerableAPI.Data;

public class AppDbContext : DbContext
{
    public AppDbContext(DbContextOptions<AppDbContext> options) : base(options) { }

    public DbSet<User> Users { get; set; } = null!;
    public DbSet<Product> Products { get; set; } = null!;
    public DbSet<Order> Orders { get; set; } = null!;
    public DbSet<AuditLog> AuditLogs { get; set; } = null!;
}
