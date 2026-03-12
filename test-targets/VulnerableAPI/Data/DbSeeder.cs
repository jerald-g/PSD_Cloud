using VulnerableAPI.Models;

namespace VulnerableAPI.Data;

public static class DbSeeder
{
    public static void Seed(AppDbContext db)
    {
        if (db.Users.Any()) return;

        // VULNERABILITY (A07): Passwords stored in plain text
        db.Users.AddRange(
            new User { Id = 1, Username = "admin", Password = "admin123", Email = "admin@company.com", Role = "Admin", CreditCard = "4111-1111-1111-1111" },
            new User { Id = 2, Username = "john", Password = "password", Email = "john@example.com", Role = "User", CreditCard = "5500-0000-0000-0004" },
            new User { Id = 3, Username = "jane", Password = "jane2024", Email = "jane@example.com", Role = "User", CreditCard = "3400-000000-00009" }
        );

        db.Products.AddRange(
            new Product { Id = 1, Name = "Laptop", Price = 999.99m, Stock = 50, Description = "High-end laptop" },
            new Product { Id = 2, Name = "Phone", Price = 499.99m, Stock = 100, Description = "Smartphone" },
            new Product { Id = 3, Name = "Tablet", Price = 299.99m, Stock = 75, Description = "10-inch tablet" }
        );

        db.SaveChanges();
    }
}
