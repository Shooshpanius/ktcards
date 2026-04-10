namespace ktcards.Server.Models
{
    public class Season
    {
        public int Id { get; set; }
        public string Name { get; set; } = string.Empty;
        public ICollection<Team> Teams { get; set; } = [];
    }
}
