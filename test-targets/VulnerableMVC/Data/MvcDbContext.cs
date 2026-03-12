using Microsoft.EntityFrameworkCore;
using VulnerableMVC.Models;

namespace VulnerableMVC.Data;

public class MvcDbContext : DbContext
{
    public MvcDbContext(DbContextOptions<MvcDbContext> options) : base(options) { }

    public DbSet<Comment> Comments { get; set; } = null!;
    public DbSet<BlogPost> BlogPosts { get; set; } = null!;
    public DbSet<UserProfile> UserProfiles { get; set; } = null!;

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<BlogPost>().HasData(
            new BlogPost { Id = 1, Title = "Welcome", Content = "Welcome to our blog!", Author = "admin" },
            new BlogPost { Id = 2, Title = "Security Tips", Content = "Always validate your inputs!", Author = "admin" }
        );
    }
}
