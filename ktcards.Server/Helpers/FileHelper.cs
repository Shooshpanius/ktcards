namespace ktcards.Server.Helpers
{
    public static class FileHelper
    {
        public static void DeleteLogo(string? logoPath)
        {
            if (string.IsNullOrEmpty(logoPath)) return;

            var wwwroot = Path.GetFullPath(Path.Combine(Directory.GetCurrentDirectory(), "wwwroot"));
            var uploadsDir = Path.Combine(wwwroot, "uploads");
            var filePath = Path.GetFullPath(Path.Combine(wwwroot, logoPath.TrimStart('/')));

            // Ensure the resolved path stays inside wwwroot/uploads
            if (!filePath.StartsWith(uploadsDir + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase))
                return;

            if (File.Exists(filePath))
                File.Delete(filePath);
        }
    }
}
