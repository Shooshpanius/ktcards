namespace ktcards.Server.Helpers
{
    public static class FileHelper
    {
        public static void DeleteLogo(string? logoPath)
        {
            if (string.IsNullOrEmpty(logoPath)) return;
            var uploadsDir = Path.GetFullPath(Path.Combine(Directory.GetCurrentDirectory(), "wwwroot", "uploads"));
            var filePath = Path.GetFullPath(Path.Combine(Directory.GetCurrentDirectory(), "wwwroot", logoPath.TrimStart('/')));
            if (!filePath.StartsWith(uploadsDir + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase))
                return;
            if (File.Exists(filePath))
                File.Delete(filePath);
        }
    }
}
