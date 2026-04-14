namespace ktcards.Server.Helpers
{
    public static class FileHelper
    {
        public static void DeleteLogo(string? logoPath)
        {
            if (string.IsNullOrEmpty(logoPath)) return;
            var uploadsDir = Path.GetFullPath(Path.Combine(Directory.GetCurrentDirectory(), "wwwroot", "uploads"));
            var filePath = Path.GetFullPath(Path.Combine(Directory.GetCurrentDirectory(), "wwwroot", logoPath.TrimStart('/')));
            var relative = Path.GetRelativePath(uploadsDir, filePath);
            if (relative.StartsWith("..") || Path.IsPathRooted(relative))
                return;
            if (File.Exists(filePath))
                File.Delete(filePath);
        }
    }
}
