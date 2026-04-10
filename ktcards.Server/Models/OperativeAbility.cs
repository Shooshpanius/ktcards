using System.Text.Json.Serialization;

namespace ktcards.Server.Models
{
    public class OperativeAbility
    {
        public int Id { get; set; }
        public int OperativeId { get; set; }
        [JsonIgnore]
        public Operative Operative { get; set; } = null!;

        public string Name { get; set; } = string.Empty;
        public string Description { get; set; } = string.Empty;
    }
}
