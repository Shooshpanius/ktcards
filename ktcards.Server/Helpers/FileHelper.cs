namespace ktcards.Server.Helpers
{
    public static class FileHelper
    {
        public static void DeleteLogo(string? logoPath)
        {
            if (string.IsNullOrEmpty(logoPath)) return;
            var filePath = Path.Combine(Directory.GetCurrentDirectory(), "wwwroot", logoPath.TrimStart('/'));
            if (File.Exists(filePath))
                File.Delete(filePath);
        }
    }
}
