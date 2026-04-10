using System.Text.Json.Serialization;

namespace ktcards.Server.Models
{
    public class FactionRule
    {
        public int Id { get; set; }
        public int TeamId { get; set; }
        [JsonIgnore]
        public Team Team { get; set; } = null!;

        public string Name { get; set; } = string.Empty;
        public string Description { get; set; } = string.Empty;
    }
}
