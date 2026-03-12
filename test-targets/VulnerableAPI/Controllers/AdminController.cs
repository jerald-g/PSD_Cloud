using Microsoft.AspNetCore.Mvc;
using System.Xml;
using System.Xml.Serialization;
using VulnerableAPI.Data;
using VulnerableAPI.Services;

namespace VulnerableAPI.Controllers;

[ApiController]
[Route("api/[controller]")]
public class AdminController : ControllerBase
{
    private readonly AppDbContext _db;
    private readonly CryptoService _crypto;

    public AdminController(AppDbContext db, CryptoService crypto)
    {
        _db = db;
        _crypto = crypto;
    }

    /// <summary>
    /// VULNERABILITY (A05): Debug/admin endpoint exposed without authentication.
    /// Returns sensitive server configuration.
    /// </summary>
    [HttpGet("debug")]
    public IActionResult Debug()
    {
        // VULNERABILITY (A05): Exposing server internals
        return Ok(new
        {
            Environment = Environment.GetEnvironmentVariables(),
            MachineName = Environment.MachineName,
            OSVersion = Environment.OSVersion.ToString(),
            CurrentDirectory = Environment.CurrentDirectory,
            ProcessId = Environment.ProcessId,
            DotnetVersion = Environment.Version.ToString(),
            // VULNERABILITY (A02): Hardcoded secrets exposed
            DatabaseConnectionString = "Data Source=vulnerable.db",
            ApiKey = "sk-12345-HARDCODED-API-KEY-67890",
            AdminPassword = "SuperSecret123!",
        });
    }

    /// <summary>
    /// VULNERABILITY (A08 - Software and Data Integrity): XML External Entity (XXE) attack.
    /// SonarQube should detect the insecure XML parser configuration.
    /// </summary>
    [HttpPost("import-xml")]
    public IActionResult ImportXml([FromBody] string xmlContent)
    {
        // VULNERABILITY (A08): XXE – XML External Entity processing enabled
        var settings = new XmlReaderSettings
        {
            DtdProcessing = DtdProcessing.Parse,  // XXE enabled!
            XmlResolver = new XmlUrlResolver()     // Allows external entity resolution
        };

        try
        {
            using var reader = XmlReader.Create(new StringReader(xmlContent), settings);
            var doc = new XmlDocument();
            doc.Load(reader);
            return Ok(new { parsed = doc.OuterXml });
        }
        catch (Exception ex)
        {
            return BadRequest(new { error = ex.Message });
        }
    }

    /// <summary>
    /// VULNERABILITY (A02): Using weak cryptographic algorithms.
    /// </summary>
    [HttpPost("encrypt")]
    public IActionResult Encrypt([FromBody] EncryptRequest request)
    {
        var encrypted = _crypto.EncryptWithDES(request.PlainText);
        var md5Hash = _crypto.HashWithMD5(request.PlainText);
        var sha1Hash = _crypto.HashWithSHA1(request.PlainText);

        return Ok(new
        {
            original = request.PlainText,
            desEncrypted = Convert.ToBase64String(encrypted),
            md5Hash,
            sha1Hash,
        });
    }

    /// <summary>
    /// VULNERABILITY (A08): Deserializing untrusted data.
    /// </summary>
    [HttpPost("deserialize")]
    public IActionResult Deserialize([FromBody] string serializedData)
    {
        // VULNERABILITY (A08): Insecure deserialization of untrusted input
        try
        {
            var bytes = Convert.FromBase64String(serializedData);
            using var ms = new MemoryStream(bytes);
            #pragma warning disable SYSLIB0011
            var formatter = new System.Runtime.Serialization.Formatters.Binary.BinaryFormatter();
            var obj = formatter.Deserialize(ms);  // Extremely dangerous!
            #pragma warning restore SYSLIB0011

            return Ok(new { type = obj?.GetType().Name, data = obj?.ToString() });
        }
        catch (Exception ex)
        {
            return BadRequest(new { error = ex.Message });
        }
    }

    /// <summary>
    /// VULNERABILITY (A10 - SSRF): Server makes requests to user-supplied URLs.
    /// ZAP should detect this SSRF vector.
    /// </summary>
    [HttpGet("fetch")]
    public async Task<IActionResult> FetchUrl([FromQuery] string url)
    {
        // VULNERABILITY (A10): Server-Side Request Forgery – no URL validation
        // Attacker can target internal services: http://169.254.169.254/latest/meta-data/
        using var httpClient = new HttpClient();
        try
        {
            var response = await httpClient.GetStringAsync(url);
            return Ok(new { url, response });
        }
        catch (Exception ex)
        {
            return BadRequest(new { error = ex.Message });
        }
    }
}

public class EncryptRequest
{
    public string PlainText { get; set; } = string.Empty;
}
