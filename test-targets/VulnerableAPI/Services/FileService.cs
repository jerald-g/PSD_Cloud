namespace VulnerableAPI.Services;

public class FileService
{
    // VULNERABILITY (A02): Hardcoded credentials
    private const string FtpUsername = "admin";
    private const string FtpPassword = "P@ssw0rd123!";
    private const string AwsSecretKey = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY";
    private const string DatabasePassword = "db_super_secret_2024";
    private const string JwtSigningKey = "MyS3cretJWT$igning#Key!ForTheApp2024DoNotShare";

    public string GetFtpCredentials() => $"{FtpUsername}:{FtpPassword}";
    public string GetAwsKey() => AwsSecretKey;
}
