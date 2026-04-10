namespace ktcards.Server.Models
{
    public class FactionEquipment
    {
        public int Id { get; set; }
        public int TeamId { get; set; }
        public Team Team { get; set; } = null!;

        public string Name { get; set; } = string.Empty;
        public int EpCost { get; set; }
        public string Description { get; set; } = string.Empty;
        public string? Restrictions { get; set; }
    }
}
