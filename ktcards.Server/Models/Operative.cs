using System.Text.Json.Serialization;

namespace ktcards.Server.Models
{
    public class Operative
    {
        public int Id { get; set; }
        public int TeamId { get; set; }
        [JsonIgnore]
        public Team Team { get; set; } = null!;

        public string Name { get; set; } = string.Empty;
        public string? Keywords { get; set; }
        public string? Movement { get; set; }
        public int ActionPointLimit { get; set; }
        public int GroupActivations { get; set; }
        public int Defence { get; set; }
        public int Save { get; set; }
        public int Wounds { get; set; }
        public string? Notes { get; set; }

        public ICollection<OperativeAbility> Abilities { get; set; } = [];
        public ICollection<OperativeAttack> Attacks { get; set; } = [];
    }
}
