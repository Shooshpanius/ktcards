using System.Text.Json.Serialization;

namespace ktcards.Server.Models
{
    public class OperativeAttack
    {
        public int Id { get; set; }
        public int OperativeId { get; set; }
        [JsonIgnore]
        public Operative Operative { get; set; } = null!;

        public string Name { get; set; } = string.Empty;
        public string AttackType { get; set; } = string.Empty; // Melee / Ranged
        public int Attacks { get; set; }
        public int HitSkill { get; set; }
        public string Damage { get; set; } = string.Empty;
        public string CriticalDamage { get; set; } = string.Empty;
        public string? SpecialRules { get; set; }
    }
}
