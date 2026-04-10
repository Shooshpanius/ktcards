namespace ktcards.Server.Models
{
    public class Team
    {
        public int Id { get; set; }
        public string Name { get; set; } = string.Empty;
        public string? LogoPath { get; set; }
        public int SeasonId { get; set; }
        public Season Season { get; set; } = null!;
    }
}
