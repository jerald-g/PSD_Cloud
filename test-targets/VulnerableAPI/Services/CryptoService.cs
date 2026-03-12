using System.Security.Cryptography;
using System.Text;

namespace VulnerableAPI.Services;

/// <summary>
/// VULNERABILITY (A02 - Cryptographic Failures): Uses weak/deprecated algorithms.
/// SonarQube should flag DES, MD5, SHA1, and hardcoded keys.
/// </summary>
public class CryptoService
{
    // VULNERABILITY (A02): Hardcoded encryption key
    private static readonly byte[] DesKey = Encoding.UTF8.GetBytes("12345678");
    private static readonly byte[] DesIv = Encoding.UTF8.GetBytes("87654321");

    /// <summary>
    /// VULNERABILITY (A02): DES is a deprecated cipher with 56-bit keys.
    /// </summary>
    public byte[] EncryptWithDES(string plainText)
    {
        #pragma warning disable SYSLIB0021
        using var des = DES.Create();
        #pragma warning restore SYSLIB0021
        des.Key = DesKey;
        des.IV = DesIv;
        des.Mode = CipherMode.ECB;  // VULNERABILITY: ECB mode is insecure

        using var ms = new MemoryStream();
        using var cs = new CryptoStream(ms, des.CreateEncryptor(), CryptoStreamMode.Write);
        var bytes = Encoding.UTF8.GetBytes(plainText);
        cs.Write(bytes, 0, bytes.Length);
        cs.FlushFinalBlock();
        return ms.ToArray();
    }

    /// <summary>
    /// VULNERABILITY (A02): MD5 is cryptographically broken.
    /// </summary>
    public string HashWithMD5(string input)
    {
        #pragma warning disable SYSLIB0021
        using var md5 = MD5.Create();
        #pragma warning restore SYSLIB0021
        var bytes = md5.ComputeHash(Encoding.UTF8.GetBytes(input));
        return Convert.ToHexString(bytes);
    }

    /// <summary>
    /// VULNERABILITY (A02): SHA1 is deprecated and vulnerable to collision attacks.
    /// </summary>
    public string HashWithSHA1(string input)
    {
        #pragma warning disable SYSLIB0021
        using var sha1 = SHA1.Create();
        #pragma warning restore SYSLIB0021
        var bytes = sha1.ComputeHash(Encoding.UTF8.GetBytes(input));
        return Convert.ToHexString(bytes);
    }

    /// <summary>
    /// VULNERABILITY (A02): Random number generator not cryptographically secure.
    /// </summary>
    public string GenerateToken()
    {
        var random = new Random();  // VULNERABILITY: Not cryptographically secure
        var token = "";
        for (int i = 0; i < 32; i++)
        {
            token += random.Next(0, 9).ToString();
        }
        return token;
    }
}
