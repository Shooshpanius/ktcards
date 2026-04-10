using Microsoft.EntityFrameworkCore;
using ktcards.Server.Models;

namespace ktcards.Server.Data
{
    public class AppDbContext(DbContextOptions<AppDbContext> options) : DbContext(options)
    {
        public DbSet<Season> Seasons => Set<Season>();
        public DbSet<Team> Teams => Set<Team>();

        public DbSet<Operative> Operatives => Set<Operative>();
        public DbSet<OperativeAbility> OperativeAbilities => Set<OperativeAbility>();
        public DbSet<OperativeAttack> OperativeAttacks => Set<OperativeAttack>();
        public DbSet<FactionRule> FactionRules => Set<FactionRule>();
        public DbSet<MarkerToken> MarkerTokens => Set<MarkerToken>();
        public DbSet<StrategyPloy> StrategyPloys => Set<StrategyPloy>();
        public DbSet<FirefightPloy> FirefightPloys => Set<FirefightPloy>();
        public DbSet<FactionEquipment> FactionEquipments => Set<FactionEquipment>();
    }
}
