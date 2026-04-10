namespace ktcards.Server.Models
{
    public class FirefightPloy
    {
        public int Id { get; set; }
        public int TeamId { get; set; }
        public Team Team { get; set; } = null!;

        public string Name { get; set; } = string.Empty;
        public int CpCost { get; set; }
        public string Description { get; set; } = string.Empty;
    }
}
