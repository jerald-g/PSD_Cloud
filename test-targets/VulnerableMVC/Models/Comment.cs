namespace VulnerableMVC.Models;

public class Comment
{
    public int Id { get; set; }
    public int BlogPostId { get; set; }
    public string Author { get; set; } = string.Empty;
    // VULNERABILITY (A03 - XSS): Content rendered without encoding
    public string Content { get; set; } = string.Empty;
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
}

public class BlogPost
{
    public int Id { get; set; }
    public string Title { get; set; } = string.Empty;
    public string Content { get; set; } = string.Empty;
    public string Author { get; set; } = string.Empty;
}

public class UserProfile
{
    public int Id { get; set; }
    public string Name { get; set; } = string.Empty;
    // VULNERABILITY (A03 - XSS): Bio rendered as raw HTML
    public string Bio { get; set; } = string.Empty;
    public string Website { get; set; } = string.Empty;
}
