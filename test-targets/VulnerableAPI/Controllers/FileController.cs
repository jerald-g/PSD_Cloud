using Microsoft.AspNetCore.Mvc;
using VulnerableAPI.Services;

namespace VulnerableAPI.Controllers;

[ApiController]
[Route("api/[controller]")]
public class FileController : ControllerBase
{
    private readonly FileService _fileService;
    private readonly ILogger<FileController> _logger;

    public FileController(FileService fileService, ILogger<FileController> logger)
    {
        _fileService = fileService;
        _logger = logger;
    }

    /// <summary>
    /// VULNERABILITY (A01 - Path Traversal): User can read arbitrary files on the server.
    /// ZAP should detect this via path traversal payloads.
    /// </summary>
    [HttpGet("read")]
    public IActionResult ReadFile([FromQuery] string path)
    {
        // VULNERABILITY (A01): Path traversal – no sanitization of input path
        // An attacker can pass ../../etc/passwd or ..\..\windows\system32\config\sam
        try
        {
            var content = System.IO.File.ReadAllText(path);
            return Ok(new { path, content });
        }
        catch (Exception ex)
        {
            // VULNERABILITY (A05): Leaking internal error details
            return BadRequest(new { error = ex.ToString() });
        }
    }

    /// <summary>
    /// VULNERABILITY (A04 - Insecure Design): Unrestricted file upload.
    /// No validation of file type, size, or content.
    /// </summary>
    [HttpPost("upload")]
    public async Task<IActionResult> Upload(IFormFile file)
    {
        // VULNERABILITY (A04): No file type validation – could upload .exe, .aspx, etc.
        // VULNERABILITY (A04): No file size limit
        // VULNERABILITY (A04): Saving to web-accessible directory
        var uploadDir = Path.Combine(Directory.GetCurrentDirectory(), "wwwroot", "uploads");
        Directory.CreateDirectory(uploadDir);

        // VULNERABILITY (A01): Using original filename without sanitization
        var filePath = Path.Combine(uploadDir, file.FileName);

        using var stream = new FileStream(filePath, FileMode.Create);
        await file.CopyToAsync(stream);

        _logger.LogInformation($"File uploaded: {filePath}");

        return Ok(new { message = "Uploaded", path = $"/uploads/{file.FileName}" });
    }

    /// <summary>
    /// VULNERABILITY (A03 - Injection): OS command injection via filename parameter.
    /// </summary>
    [HttpGet("info")]
    public IActionResult FileInfo([FromQuery] string filename)
    {
        // VULNERABILITY (A03): OS Command Injection
        var process = new System.Diagnostics.Process();
        process.StartInfo.FileName = "cmd.exe";
        process.StartInfo.Arguments = $"/c dir {filename}";  // Direct injection point
        process.StartInfo.RedirectStandardOutput = true;
        process.StartInfo.UseShellExecute = false;
        process.Start();

        var output = process.StandardOutput.ReadToEnd();
        process.WaitForExit();

        return Ok(new { command = $"dir {filename}", output });
    }

    /// <summary>
    /// VULNERABILITY (A05): Directory listing enabled – reveals server structure.
    /// </summary>
    [HttpGet("list")]
    public IActionResult ListDirectory([FromQuery] string directory = ".")
    {
        // VULNERABILITY (A01/A05): Arbitrary directory listing
        try
        {
            var files = Directory.GetFiles(directory);
            var dirs = Directory.GetDirectories(directory);
            return Ok(new { directory, files, subdirectories = dirs });
        }
        catch (Exception ex)
        {
            return BadRequest(new { error = ex.Message });
        }
    }
}
