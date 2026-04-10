using Microsoft.EntityFrameworkCore;
using ktcards.Server.Models;

namespace ktcards.Server.Data
{
    public class AppDbContext(DbContextOptions<AppDbContext> options) : DbContext(options)
    {
        public DbSet<Season> Seasons => Set<Season>();
        public DbSet<Team> Teams => Set<Team>();
    }
}
